import { useEffect, useRef, useState } from 'react';
import type { MLCEngine } from '@mlc-ai/web-llm';
import type { Chunk, ChunkArtifact } from '../core/types';
import { record } from '../consent/auditLog';

/**
 * Assistant step: ask questions about the chunks made in the Process step.
 * The model runs inside this tab with WebLLM (WebGPU). No server, no API, no cost.
 * Retrieval mirrors chat_server.py /chat_live: keyword overlap, top 4 chunks.
 */

const MODELS = [
  { id: 'Llama-3.2-3B-Instruct-q4f16_1-MLC', label: 'Llama 3.2 3B (better answers, about 2 GB)' },
  { id: 'Llama-3.2-1B-Instruct-q4f16_1-MLC', label: 'Llama 3.2 1B (faster, about 0.9 GB)' },
];

const STOP = new Set(
  'the a an and or of to in on for is are was were what how why who when which does did do with by as at from that this it be'.split(' ')
);

const SYSTEM_PROMPT =
  "Answer ONLY using the context below. Be brief and factual. If the answer is not in the context, say 'Not found in the document.'";

const TOP_K = 4;

type Message = { role: 'user' | 'ai'; text: string; sources?: Chunk[] };

function tokenize(text: string): string[] {
  return (text.toLowerCase().match(/[a-z0-9$%]+/g) ?? []).filter((w) => w.length > 1 && !STOP.has(w));
}

/**
 * Score chunks by shared question words, weighting rare words higher (IDF).
 * A word found in every chunk ("ai") counts for little; a word found in one
 * chunk ("moderna") counts for a lot. Keep the best 4.
 */
function retrieve(question: string, chunks: Chunk[]): Chunk[] {
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
      const webllm = await import('@mlc-ai/web-llm');
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
    const sources = retrieve(q, chunks.chunks);
    setMessages((m) => [
      ...m,
      { role: 'user', text: q },
      { role: 'ai', text: sources.length ? 'Thinking…' : 'Not found in the document.', sources },
    ]);
    record('ask', 'artifact', chunks.doc_id, 'allow', `${sources.length}_chunks_retrieved`);

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
        temperature: 0.1,
        max_tokens: 400,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: `Context:\n${context}\n\nQuestion: ${q}` },
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