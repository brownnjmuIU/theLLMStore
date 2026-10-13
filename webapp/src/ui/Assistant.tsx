import { useEffect, useMemo, useRef, useState } from 'react';
import type { MLCEngine } from '@mlc-ai/web-llm';
import type { Chunk, ChunkArtifact } from '../core/types';
import { record } from '../consent/auditLog';
import { SYSTEM_PROMPT, documentQuality, looksGarbled, retrieve, type Mode } from './retrieval';

/**
 * Assistant step: ask questions about the chunks made in the Process step.
 * The model runs inside this tab with WebLLM (WebGPU). No server, no API, no cost.
 * Passage selection lives in ./retrieval.ts (tested in tests/stress/).
 *
 * Week 3 hardening, after the Assistant returned gibberish on Edge/Windows:
 *   - After loading, a one-line self-test checks the GPU produces real words. Some Windows GPU
 *     drivers advertise 16-bit math but compute it wrongly; then we switch to the 32-bit
 *     ("compatibility") build of the same model automatically.
 *   - Every answer is checked for the same corruption, with a one-click switch.
 *   - No more frequency_penalty: it pushed small models away from repeating names from the
 *     document ("Jev", "Doom"), which produced fragments like "Jev J juev".
 *   - GPU crashes, out-of-memory and empty or unreadable files get plain-language messages.
 */

const MODELS = [
  { id: 'Llama-3.2-3B-Instruct-q4f16_1-MLC', label: 'Llama 3.2 3B (recommended, about 2 GB)' },
  { id: 'Llama-3.2-1B-Instruct-q4f16_1-MLC', label: 'Llama 3.2 1B (faster, simpler answers, about 0.9 GB)' },
  { id: 'Llama-3.2-3B-Instruct-q4f32_1-MLC', label: 'Llama 3.2 3B, compatibility mode (use if answers look like gibberish, about 3 GB)' },
  { id: 'Llama-3.2-1B-Instruct-q4f32_1-MLC', label: 'Llama 3.2 1B, compatibility mode (about 1.1 GB)' },
  { id: 'Llama-3.1-8B-Instruct-q4f16_1-MLC', label: 'Llama 3.1 8B (same model as the desktop app, about 5 GB, needs a strong laptop)' },
];

/** The 32-bit build of a 16-bit model, or null if it already is one. */
const compatibilityVersion = (id: string) => (id.includes('q4f16_1') ? id.replace('q4f16_1', 'q4f32_1') : null);

const MODE_LABEL: Record<Mode, string> = {
  whole: 'read the whole document',
  overview: 'passages from across the document',
  section: 'the matching section',
  keyword: 'passages that share words with your question',
  fallback: 'no exact word match, so passages from across the document',
};

type Message = { role: 'user' | 'ai'; text: string; sources?: Chunk[]; how?: string; garbled?: boolean };

/** Turn WebLLM / WebGPU errors into something a student can act on. */
function friendlyError(raw: string): { text: string; reset: boolean } {
  const m = raw.toLowerCase();
  if (m.includes('device') && (m.includes('lost') || m.includes('destroyed')))
    return { text: 'The graphics card stopped responding (this can happen when the laptop sleeps or another tab uses the GPU). Load the model again.', reset: true };
  if (m.includes('out of memory') || m.includes('outofmemory') || m.includes('allocation'))
    return { text: 'Not enough graphics memory for this model. Close other tabs, or load the 1B model instead.', reset: true };
  if (m.includes('context window') || m.includes('prompt tokens exceed'))
    return { text: 'That question pulled in more text than the model can read at once. Ask about something more specific.', reset: false };
  if (m.includes('adapter') || m.includes('webgpu'))
    return { text: 'This browser could not start the graphics card for AI. Update Chrome or Edge, make sure hardware acceleration is on (Settings, System), and try again.', reset: true };
  if (m.includes('fetch') || m.includes('network') || m.includes('cache'))
    return { text: 'The model download was interrupted. Check the internet connection and load the model again; the parts already downloaded are kept.', reset: true };
  return { text: `Something went wrong: ${raw}`, reset: false };
}

export function Assistant({ chunks }: { chunks: ChunkArtifact | null }) {
  const engine = useRef<MLCEngine | null>(null);
  const chatBox = useRef<HTMLDivElement>(null);

  const [modelId, setModelId] = useState('Llama-3.2-3B-Instruct-q4f16_1-MLC');
  const [loadedId, setLoadedId] = useState('');
  const [modelState, setModelState] = useState<'off' | 'loading' | 'ready' | 'error'>('off');
  const [loadNote, setLoadNote] = useState('');
  const [modelNote, setModelNote] = useState('');
  const [progress, setProgress] = useState(0);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [answering, setAnswering] = useState(false);

  const hasWebGPU = typeof navigator !== 'undefined' && 'gpu' in navigator;
  const quality = useMemo(() => (chunks ? documentQuality(chunks.chunks) : null), [chunks]);
  const docText = useMemo(() => (chunks ? chunks.chunks.map((c) => c.text).join('\n') : ''), [chunks]);

  // A new document starts a fresh conversation.
  useEffect(() => {
    setMessages([]);
  }, [chunks?.doc_id]);

  // Keep the newest message in view.
  useEffect(() => {
    if (chatBox.current) chatBox.current.scrollTop = chatBox.current.scrollHeight;
  }, [messages]);

  /** One tiny question with a known answer. Garbage here means the GPU math is broken. */
  const selfTest = async (): Promise<boolean> => {
    if (!engine.current) return false;
    const reply = await engine.current.chat.completions.create({
      temperature: 0,
      max_tokens: 12,
      messages: [{ role: 'user', content: 'What is the capital of France? Reply with one word.' }],
    });
    const text = reply.choices[0]?.message?.content ?? '';
    await engine.current.resetChat();
    return /paris/i.test(text) && !looksGarbled(text);
  };

  const loadModel = async (id = modelId, isRetry = false) => {
    setModelState('loading');
    setLoadNote('Starting…');
    setProgress(0);
    if (!isRetry) setModelNote('');
    try {
      if (engine.current) {
        await engine.current.unload().catch(() => undefined);
        engine.current = null;
      }
      const webllm = await import('./webllm');
      engine.current = await webllm.CreateMLCEngine(id, {
        initProgressCallback: (report) => {
          setLoadNote(report.text);
          setProgress(report.progress);
        },
      });

      setLoadNote('Checking that the model works on this computer…');
      const ok = await selfTest();
      if (!ok) {
        const fallback = compatibilityVersion(id);
        record('load_model', 'local_model', id, 'deny', 'self_test_failed_garbled_output');
        if (fallback && !isRetry) {
          setModelNote(
            'Your graphics card gave wrong results with the fast 16-bit model, so the Assistant switched to compatibility mode (32-bit). It is a little slower but reliable.'
          );
          setModelId(fallback);
          return loadModel(fallback, true);
        }
        throw new Error(
          'The model loaded but produced unreadable output on this computer. Try Chrome instead of Edge, update the graphics driver, or use the desktop app.'
        );
      }

      setLoadedId(id);
      setModelState('ready');
      record('load_model', 'local_model', id, 'allow', 'runs_in_browser_webgpu_self_test_passed');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setModelState('error');
      setLoadNote(message.startsWith('The model loaded') ? message : friendlyError(message).text);
      record('load_model', 'local_model', id, 'deny', `failed: ${message}`);
    }
  };

  const switchToCompatibility = () => {
    const fallback = compatibilityVersion(loadedId);
    if (!fallback) return;
    setModelId(fallback);
    setModelNote('Switched to compatibility mode (32-bit) after an unreadable answer.');
    void loadModel(fallback, true);
  };

  const stop = () => {
    void engine.current?.interruptGenerate();
  };

  const ask = async () => {
    const q = question.trim();
    if (!q || !chunks || !engine.current || answering) return;

    setQuestion('');
    const picked = retrieve(q, chunks.chunks);
    const sources = picked.chunks;
    const how = MODE_LABEL[picked.mode];
    const empty =
      quality?.level === 'empty'
        ? quality.message
        : 'Not found in the document.';
    setMessages((m) => [
      ...m,
      { role: 'user', text: q },
      { role: 'ai', text: sources.length ? 'Thinking…' : empty, sources, how: sources.length ? how : undefined },
    ]);
    record('ask', 'artifact', chunks.doc_id, 'allow', `${picked.mode}_${sources.length}_chunks_retrieved`);
    if (!sources.length) return;

    setAnswering(true);
    const updateAnswer = (patch: Partial<Message>) =>
      setMessages((m) => {
        const copy = [...m];
        const last = copy[copy.length - 1];
        if (last) copy[copy.length - 1] = { ...last, ...patch };
        return copy;
      });

    const context = sources.map((c) => `[${c.chunk_id}]\n${c.text}`).join('\n\n');

    try {
      const stream = await engine.current.chat.completions.create({
        stream: true,
        temperature: 0.2,
        max_tokens: 600,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: `${picked.note ? picked.note + '\n\n' : ''}Document passages:\n${context}\n\nQuestion: ${q}` },
        ],
      });
      let answer = '';
      for await (const part of stream) {
        answer += part.choices[0]?.delta?.content ?? '';
        updateAnswer({ text: answer });
      }
      if (!answer.trim()) {
        updateAnswer({ text: 'The model returned an empty answer. Try asking again in different words.' });
      } else if (looksGarbled(answer, docText)) {
        record('answer', 'artifact', chunks.doc_id, 'deny', 'garbled_output_detected');
        updateAnswer({
          garbled: true,
          text:
            answer +
            '\n\n⚠ This answer looks corrupted. That is a graphics-card problem, not a problem with your document. Switch to compatibility mode below and ask again.',
        });
      }
    } catch (error) {
      const { text, reset } = friendlyError(error instanceof Error ? error.message : String(error));
      updateAnswer({ text });
      if (reset) {
        engine.current = null;
        setModelState('off');
      }
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

          {quality && quality.level !== 'ok' && (
            <p className={`assistant-notice ${quality.level === 'thin' ? '' : 'warn'}`}>{quality.message}</p>
          )}
          {modelNote && <p className="assistant-notice">{modelNote}</p>}

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
              {modelState === 'error' && <p className="assistant-notice warn">{loadNote}</p>}
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
                    {m.how && <p className="assistant-how">How the passages were picked: {m.how}</p>}
                    {m.garbled && compatibilityVersion(loadedId) && (
                      <button type="button" className="button secondary" onClick={switchToCompatibility}>
                        Switch to compatibility mode
                      </button>
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
                {answering ? (
                  <button type="button" className="button secondary" onClick={stop}>
                    Stop
                  </button>
                ) : (
                  <button
                    type="button"
                    className="button primary"
                    onClick={() => void ask()}
                    disabled={!question.trim()}
                  >
                    Ask
                  </button>
                )}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}
