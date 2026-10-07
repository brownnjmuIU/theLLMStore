import { useEffect, useRef, useState } from 'react';
import type { MLCEngine } from '@mlc-ai/web-llm';
import type { Chunk, ChunkArtifact } from '../core/types';
import { record } from '../consent/auditLog';

/**
 * Assistant step: ask questions about the chunks made in the Process step.
 * The model runs inside this tab with WebLLM (WebGPU). No server, no API, no cost.
 * Retrieval: summary questions get passages from across the document, section questions
 * get that section, everything else uses keyword search weighted by word rarity.
 */

const MODELS = [
  { id: 'Llama-3.2-3B-Instruct-q4f16_1-MLC', label: 'Llama 3.2 3B (recommended, about 2 GB)' },
  { id: 'Llama-3.2-1B-Instruct-q4f16_1-MLC', label: 'Llama 3.2 1B (faster, simpler answers, about 0.9 GB)' },
  { id: 'Llama-3.1-8B-Instruct-q4f16_1-MLC', label: 'Llama 3.1 8B (same model as the desktop app, about 5 GB, needs a strong laptop)' },
];

const STOP = new Set(
  ('the a an and or of to in on for is are was were what how why who when which does did do with by as at from that this it be ' +
    'can could would should will you your me my u please tell give provide explain show describe its there their they them any also into than then has have had been not all more some about')
    .split(' ')
);

/** Questions made only of these words ask about the whole document (same idea as the desktop retriever). */
const OVERVIEW = new Set(
  'summary summarize summarise summarization overview document doc file pdf paper article content contents main point points idea ideas topic topics gist key takeaway takeaways whole entire'.split(' ')
);

/** Section questions: find the heading in the text and send that part of the document. */
const SECTIONS: { name: string; pattern: string }[] = [
  { name: 'Abstract', pattern: 'abstract' },
  { name: 'Introduction', pattern: 'introduction' },
  { name: 'Background', pattern: 'background|related work|literature review' },
  { name: 'Methods', pattern: 'methods?|methodology|approach|data and methods|research design|study design|empirical strategy|procedures?' },  
  { name: 'Discussion', pattern: 'discussion' },
  { name: 'Limitations', pattern: 'limitations?' },
  { name: 'Conclusion', pattern: 'conclusions?|concluding remarks' },
];

const SYSTEM_PROMPT =
  'You are the PPLLM Assistant. Answer the question using only the document passages provided. ' +
  'Write in complete sentences, usually 2 to 5. When the question asks for a summary or for several items, use a short list. ' +
  'Explain in your own words; do not copy citation markers, page headers or broken fragments. ' +
  'If the passages only partly answer the question, answer the part they support and say what is missing. ' +
  'Only if the passages contain nothing related to the question, reply exactly: Not found in the document.';

const TOP_K = 5;

type Message = { role: 'user' | 'ai'; text: string; sources?: Chunk[] };
type Mode = 'keyword' | 'overview' | 'section';

/** Lowercase words, minus filler words; a trailing plural "s" is dropped so "methods" matches "method". */
function tokenize(text: string): string[] {
  return (text.toLowerCase().match(/[a-z0-9$%]+/g) ?? [])
    .filter((w) => w.length > 1 && !STOP.has(w))
    .map((w) => (w.length > 4 && w.endsWith('s') && !w.endsWith('ss') ? w.slice(0, -1) : w));
}

/** Chunks spread evenly from the start to the end of the document, for summary questions. */
function spreadAcross(chunks: Chunk[], k: number): Chunk[] {
  if (chunks.length <= k) return chunks;
  const picks = new Set<number>();
  for (let i = 0; i < k; i++) picks.add(Math.round((i * (chunks.length - 1)) / (k - 1)));
  return chunks.filter((_, i) => picks.has(i));
}

/** Index of the chunk where the reference list starts, or chunks.length if there is none. */
function referencesStart(chunks: Chunk[]): number {
  const i = chunks.findIndex((c) => /(^|\n)[ \t]*(references|bibliography|works cited)[ \t]*(\n|$)/i.test(c.text));
  return i > 0 ? i : chunks.length;
}

/** A section heading on its own short line, plus the two chunks after it. Never looks in the reference list. */
function findSection(question: string, chunks: Chunk[]): { name: string; chunks: Chunk[] } | null {
  const q = question.toLowerCase();
  const body = chunks.slice(0, referencesStart(chunks));
  for (const s of SECTIONS) {
    if (!new RegExp(`\\b(${s.pattern})\\b`).test(q)) continue;
    const heading = new RegExp(`(^|\\n)[ \\t]*([0-9ivx]+(\\.[0-9]+)*\\.?[ \\t]+)?(${s.pattern})\\b[^\\n]{0,30}(\\n|$)`, 'i');
    const start = body.findIndex((c) => heading.test(c.text));
    if (start >= 0) return { name: s.name, chunks: body.slice(start, start + 3) };
  }
  return null;
}


/**
 * Score chunks by shared question words, weighting rare words higher (IDF).
 * A word found in every chunk ("ai") counts for little; a word found in one
 * chunk ("moderna") counts for a lot.
 */
function keywordSearch(question: string, chunks: Chunk[]): Chunk[] {
  const q = new Set(tokenize(question));
  const chunkWords = chunks.map((chunk) => new Set(tokenize(chunk.text)));
  const n = chunks.length;

  const idf = new Map<string, number>();
  q.forEach((w) => {
    const df = chunkWords.filter((words) => words.has(w)).length;
    idf.set(w, df === 0 ? 0 : Math.log(1 + n / df));
  });

  return chunks
    .map((chunk, i) => {
      let score = 0;
      q.forEach((w) => {
        if (chunkWords[i]?.has(w)) score += idf.get(w) ?? 0;
      });
      return { chunk, score };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, TOP_K)
    .map((s) => s.chunk);
}

/** Pick the passages to send: whole-document overview, a named section, or keyword search. */
function retrieve(question: string, chunks: Chunk[]): { mode: Mode; note: string; chunks: Chunk[] } {
  const q = question.toLowerCase();
  const wantsRefs = /\b(references?|citations?|cited|bibliography)\b/.test(q);
  const body = wantsRefs ? chunks : chunks.slice(0, referencesStart(chunks));
  const words = (q.match(/[a-z0-9$%]+/g) ?? []).filter((w) => w.length > 1 && !STOP.has(w));

  if (words.length > 0 && words.every((w) => OVERVIEW.has(w))) {
    return {
      mode: 'overview',
      note: 'These passages are spread from the start to the end of the document. Use them to describe what the whole document is about.',
      chunks: spreadAcross(body, TOP_K),
    };
  }

  const section = findSection(question, chunks);
  if (section) {
    return {
      mode: 'section',
      note: `These passages are the ${section.name} section of the document. Summarize what it says.`,
      chunks: section.chunks,
    };
  }

  const found = keywordSearch(question, body);
  if (found.length) return { mode: 'keyword', note: '', chunks: found };

  // A section was named but the document has no heading with that name: describe the document instead.
  const asked = SECTIONS.find((s) => new RegExp(`\\b(${s.pattern})\\b`).test(q));
  if (asked) {
    return {
      mode: 'overview',
      note: `This document has no section titled ${asked.name}. Mention that in one short sentence, then answer the question from these passages anyway, which are spread across the document. For methods, describe how the work was done: the research design or approach, the data, sources or participants, and how the results were measured or analyzed. Only describe the parts these passages actually mention, and skip the rest.`,
      chunks: spreadAcross(body, TOP_K),
    };
  }
  return { mode: 'keyword', note: '', chunks: [] };
}

export function Assistant({ chunks }: { chunks: ChunkArtifact | null }) {
  const engine = useRef<MLCEngine | null>(null);
  const chatBox = useRef<HTMLDivElement>(null);

  const [modelId, setModelId] = useState('Llama-3.2-3B-Instruct-q4f16_1-MLC');
  const [modelState, setModelState] = useState<'off' | 'loading' | 'ready' | 'error'>('off');
  const [loadNote, setLoadNote] = useState('');
  const [progress, setProgress] = useState(0);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [answering, setAnswering] = useState(false);

  const hasWebGPU = typeof navigator !== 'undefined' && 'gpu' in navigator;

  // A new document starts a fresh conversation.
  useEffect(() => {
    setMessages([]);
  }, [chunks?.doc_id]);

  // Keep the newest message in view.
  useEffect(() => {
    if (chatBox.current) chatBox.current.scrollTop = chatBox.current.scrollHeight;
  }, [messages]);

  const loadModel = async () => {
    setModelState('loading');
    setLoadNote('Starting…');
    setProgress(0);
    try {
      const webllm = await import('./webllm');
      engine.current = await webllm.CreateMLCEngine(modelId, {
        initProgressCallback: (report) => {
          setLoadNote(report.text);
          setProgress(report.progress);
        },
      });
      setModelState('ready');
      record('load_model', 'local_model', modelId, 'allow', 'runs_in_browser_webgpu');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setModelState('error');
      setLoadNote(message);
      record('load_model', 'local_model', modelId, 'deny', `failed: ${message}`);
    }
  };

  const ask = async () => {
    const q = question.trim();
    if (!q || !chunks || !engine.current || answering) return;

    setQuestion('');
    setAnswering(true);
    const picked = retrieve(q, chunks.chunks);
    const sources = picked.chunks;
    setMessages((m) => [
      ...m,
      { role: 'user', text: q },
      { role: 'ai', text: sources.length ? 'Thinking…' : 'Not found in the document.', sources },
    ]);
    record('ask', 'artifact', chunks.doc_id, 'allow', `${picked.mode}_${sources.length}_chunks_retrieved`);

    if (!sources.length) {
      setAnswering(false);
      return;
    }

    const updateAnswer = (text: string) =>
      setMessages((m) => {
        const copy = [...m];
        const last = copy[copy.length - 1];
        if (last) copy[copy.length - 1] = { ...last, text };
        return copy;
      });

    const context = sources.map((c) => `[${c.chunk_id}]\n${c.text}`).join('\n\n');

    try {
      const stream = await engine.current.chat.completions.create({
        stream: true,
        temperature: 0.3,
        max_tokens: 700,
        frequency_penalty: 0.3,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: `${picked.note ? picked.note + '\n\n' : ''}Document passages:\n${context}\n\nQuestion: ${q}` },
        ],
      });
      let answer = '';
      for await (const part of stream) {
        answer += part.choices[0]?.delta?.content ?? '';
        updateAnswer(answer);
      }
    } catch (error) {
      updateAnswer(`Something went wrong: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setAnswering(false);
    }
  };

  return (
    <section className="browser-panel active">
      <div className="panel-heading">
        <h2>Ask your document</h2>
        <p>
          The AI model runs inside this browser tab on your own device. Your document and your
          questions are never sent anywhere.
        </p>
      </div>

      {!chunks ? (
        <p className="fine-print">Create chunks first. The Assistant answers using them.</p>
      ) : !hasWebGPU ? (
        <p className="fine-print">
          This browser cannot run the AI model. Please use a recent version of Chrome or Edge on a
          laptop or desktop.
        </p>
      ) : (
        <>
          <div className="artifact-panel">
            <div>
              <strong>{chunks.source_filename}</strong>
              <p>{chunks.total_chunks} chunks ready to search</p>
            </div>
            <span className="badge">{modelState === 'ready' ? 'Model ready' : 'Model not loaded'}</span>
          </div>

          {modelState !== 'ready' && (
            <div className="assistant-load">
              <label>
                Model
                <select
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  disabled={modelState === 'loading'}
                >
                  {MODELS.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </label>
              <p className="fine-print">
                The first load downloads the model once. After that it is cached in this browser
                and starts in seconds.
              </p>
              {modelState === 'loading' && (
                <>
                  <progress max={1} value={progress} />
                  <p className="fine-print">{loadNote}</p>
                </>
              )}
              {modelState === 'error' && <p className="fine-print">⚠ {loadNote}</p>}
              <button
                type="button"
                className="button primary"
                onClick={() => void loadModel()}
                disabled={modelState === 'loading'}
              >
                {modelState === 'loading' ? 'Loading model…' : 'Load AI model'}
              </button>
            </div>
          )}

          {modelState === 'ready' && (
            <>
              <div className="assistant-chat" ref={chatBox}>
                {messages.length === 0 && (
                  <p className="fine-print">
                    Ask a question about {chunks.source_filename}. Answers cite the chunks they
                    came from. Hover a source to see its text.
                  </p>
                )}
                {messages.map((m, i) => (
                  <div key={i} className={`assistant-msg ${m.role}`}>
                    <p>{m.text}</p>
                    {m.sources && m.sources.length > 0 && (
                      <div className="chunk-row">
                        {m.sources.map((s) => (
                          <span key={s.chunk_id} title={s.text}>
                            Source {s.chunk_id}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="assistant-ask">
                <input
                  type="text"
                  value={question}
                  placeholder="Ask about the processed chunks…"
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void ask();
                  }}
                  disabled={answering}
                />
                <button
                  type="button"
                  className="button primary"
                  onClick={() => void ask()}
                  disabled={answering || !question.trim()}
                >
                  {answering ? 'Answering…' : 'Ask'}
                </button>
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}