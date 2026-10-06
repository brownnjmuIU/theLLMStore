import { useCallback, useEffect, useRef, useState } from 'react';
import { DEFAULT_CHUNK_OPTIONS, type ChunkArtifact, type RawArtifact } from '../core/types';
import { matchedKeywords } from '../consent/sensitive';
import {
  clearEntries,
  exportAuditJson,
  getEntries,
  record,
  subscribe,
  type AuditEntry,
} from '../consent/auditLog';
import { encryptArtifact } from '../crypto/artifactCrypto';
import { exportKeyPair, generateKeyPair } from '../crypto/keyManager';
import {
  DESKTOP_ONLY_EXTENSIONS,
  extractFromFile,
  getExtension,
  PLANNED_EXTENSIONS,
  SUPPORTED_EXTENSIONS,
} from '../extractors';
import {
  buildRawArtifact,
  chunkArtifactFilename,
  downloadArtifact,
  downloadBytes,
  downloadText,
  rawArtifactFilename,
  serialiseArtifact,
} from '../storage/artifacts';
import {
  clearAll,
  deleteArtifact,
  listArtifacts,
  saveArtifact,
  type StoredArtifact,
} from '../storage/db';
import { processInWorker } from '../workers/client';
import { Assistant } from './Assistant';
import './app.css';

/**
 * Reuses the class names in website/styles.css rather than introducing a second
 * design system. Small additions live in app.css, using the same design tokens.
 *
 * Step rail: Ingest / Process / Artifacts / Audit. The original simulation's
 * third step was "Assistant", which is out of scope for the parity port.
 */

type Step = 'ingest' | 'process' | 'artifacts' | 'assistant' | 'audit';
type Status = 'idle' | 'working' | 'ready' | 'error';

const STEPS: { key: Step; label: string; hint: string }[] = [
  { key: 'ingest', label: 'Ingest', hint: 'Choose a file' },
  { key: 'process', label: 'Process', hint: 'Clean and chunk' },
  { key: 'artifacts', label: 'Artifacts', hint: 'Download output' },
  { key: 'assistant', label: 'Assistant', hint: 'Ask your document' },
  { key: 'audit', label: 'Audit', hint: 'What happened' },
];

const ACCEPT = SUPPORTED_EXTENSIONS.map((e) => `.${e}`).join(',');

export function App({ embedded = false }: { embedded?: boolean }) {
  const [step, setStep] = useState<Step>('ingest');
  const [status, setStatus] = useState<Status>('idle');
  const [statusNote, setStatusNote] = useState('Ready');

  const [file, setFile] = useState<File | null>(null);
  const [pendingSensitive, setPendingSensitive] = useState<File | null>(null);
  const [raw, setRaw] = useState<RawArtifact | null>(null);
  const [chunks, setChunks] = useState<ChunkArtifact | null>(null);

  const [chunkSize, setChunkSize] = useState(DEFAULT_CHUNK_OPTIONS.chunk_size);
  const [chunkOverlap, setChunkOverlap] = useState(DEFAULT_CHUNK_OPTIONS.chunk_overlap);

  const [encryptEnabled, setEncryptEnabled] = useState(false);
  const [persistEnabled, setPersistEnabled] = useState(false);
  const [keyPair, setKeyPair] = useState<CryptoKeyPair | null>(null);
  const [encrypted, setEncrypted] = useState<{ bytes: Uint8Array; filename: string } | null>(null);

  const [saved, setSaved] = useState<StoredArtifact[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>(getEntries());

  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => subscribe(setAudit), []);

  const refreshSaved = useCallback(async () => {
    try {
      setSaved(await listArtifacts());
    } catch {
      // Private browsing can block IndexedDB entirely. Not fatal — the app is
      // ephemeral by default, so persistence is a bonus rather than a dependency.
      setSaved([]);
    }
  }, []);

  useEffect(() => {
    void refreshSaved();
  }, [refreshSaved]);

  const fail = useCallback((message: string) => {
    setStatus('error');
    setStatusNote(message);
  }, []);

  /** Reject unsupported types with a message that says WHY, not just "no". */
  const describeUnsupported = (filename: string): string | null => {
    const extension = getExtension(filename);
    if ((SUPPORTED_EXTENSIONS as readonly string[]).includes(extension)) return null;
    if ((DESKTOP_ONLY_EXTENSIONS as readonly string[]).includes(extension)) {
      return `.${extension} files are supported in the desktop app only — video transcription needs a large local model that is impractical to download in a browser.`;
    }
    if ((PLANNED_EXTENSIONS as readonly string[]).includes(extension)) {
      return `.${extension} files are not supported yet.`;
    }
    return `.${extension || '(no extension)'} files are not supported.`;
  };

  const acceptFile = useCallback((chosen: File) => {
    setFile(chosen);
    setRaw(null);
    setChunks(null);
    setEncrypted(null);
    setStatus('idle');
    setStatusNote('File selected');
    record('select', 'local_file', chosen.name, 'allow', 'user_chose_file');
  }, []);

  const onFileChosen = (event: React.ChangeEvent<HTMLInputElement>) => {
    const chosen = event.target.files?.[0];
    if (!chosen) return;

    const problem = describeUnsupported(chosen.name);
    if (problem) {
      record('select', 'local_file', chosen.name, 'deny', 'unsupported_file_type');
      fail(problem);
      setFile(null);
      return;
    }

    if (matchedKeywords(chosen.name).length > 0) {
      setPendingSensitive(chosen);
      return;
    }
    acceptFile(chosen);
  };

  const runExtract = async () => {
    if (!file) return;
    setStatus('working');
    setStatusNote('Reading file…');

    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      const extraction = await extractFromFile(file.name, bytes);
      const artifact = await buildRawArtifact(file.name, getExtension(file.name), extraction);

      setRaw(artifact);
      setStatus('ready');
      setStatusNote(`Extracted ${artifact.text.length.toLocaleString()} characters`);
      record('read', 'local_file', file.name, 'allow', `extracted_${artifact.text.length}_chars`);
      setStep('process');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      record('read', 'local_file', file.name, 'deny', `extraction_failed: ${message}`);
      fail(message);
    }
  };

  const runChunk = async () => {
    if (!raw) return;
    setStatus('working');
    setEncrypted(null);

    try {
      const artifact = await processInWorker(
        raw,
        { chunk_size: chunkSize, chunk_overlap: chunkOverlap },
        { onProgress: (_stage, note) => setStatusNote(`${note}…`) }
      );
      setChunks(artifact);
      record('chunk', 'artifact', artifact.doc_id, 'allow', `${artifact.total_chunks}_chunks`);

      if (encryptEnabled) {
        setStatusNote('Encrypting…');
        const pair = keyPair ?? (await generateKeyPair());
        if (!keyPair) setKeyPair(pair);

        const result = await encryptArtifact(
          serialiseArtifact(artifact),
          pair.publicKey,
          chunkArtifactFilename(artifact)
        );
        setEncrypted(result);
        record('encrypt', 'artifact', artifact.doc_id, 'allow', 'rsa2048_aes256gcm');
      }

      if (persistEnabled) {
        await saveArtifact(raw, artifact);
        await refreshSaved();
        record('persist', 'artifact', artifact.doc_id, 'allow', 'user_opted_in');
      }

      setStatus('ready');
      setStatusNote(`${artifact.total_chunks} chunks ready`);
      setStep('artifacts');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      record('chunk', 'artifact', raw.doc_id, 'deny', `failed: ${message}`);
      fail(message);
    }
  };

  const exportKeys = async () => {
    if (!keyPair) return;
    const { privateKeyPem, publicKeyPem } = await exportKeyPair(keyPair);
    downloadText(privateKeyPem, 'private_key.pem');
    downloadText(publicKeyPem, 'public_key.pem');
    record('export', 'keypair', 'rsa2048', 'allow', 'user_requested_export');
  };

  const busy = status === 'working';

  return (
    <>
      {/* The host page supplies its own header when this is embedded. */}
      {!embedded && (
        <header className="site-header">
          <nav className="nav">
            <a className="brand" href="/">
              theLLMStore
            </a>
            <div className="nav-links">
              <a href="/ppllm-studio.html">Windows app</a>
              <a href="/index.html">Resources</a>
            </div>
          </nav>
        </header>
      )}

      <div
        id={embedded ? undefined : 'main'}
        className={embedded ? undefined : 'section rounded-section'}
      >
        <div className="browser-app">
          <div className="browser-app-topbar">
            <div>
              <strong>PPLLM Studio</strong>
              <p className="fine-print">Everything runs in this tab</p>
            </div>
            <span className="badge">
              {status === 'error' ? '⚠ ' : ''}
              {statusNote}
            </span>
          </div>

          <div className="browser-workspace">
            <aside className="browser-sidebar">
              {STEPS.map((entry, index) => (
                <button
                  key={entry.key}
                  type="button"
                  className={`browser-step${step === entry.key ? ' active' : ''}`}
                  onClick={() => setStep(entry.key)}
                >
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <div className="step-body">
                    <strong>{entry.label}</strong>
                    <small>{entry.hint}</small>
                  </div>
                </button>
              ))}
            </aside>

            <div className="browser-main">
              {step === 'ingest' && (
                <section className="browser-panel active">
                  <div className="panel-heading">
                    <h2>Choose a file</h2>
                    <p>
                      Your file is read inside this browser tab. It is never uploaded, and no
                      server is involved at any point.
                    </p>
                  </div>

                  <div className="file-surface">
                    <div>
                      <input
                        ref={fileInput}
                        type="file"
                        accept={ACCEPT}
                        onChange={onFileChosen}
                        aria-label="Choose a file to process"
                      />
                      <p>
                        PDF, Word (.docx), PowerPoint (.pptx) and platform exports (.json).
                        Images need OCR and video needs a speech model — both stay in the
                        desktop app for now.
                      </p>
                    </div>
                  </div>

                  {file && (
                    <div className="file-meta">
                      <strong>{file.name}</strong>
                      <span>{(file.size / 1024).toFixed(0)} KB</span>
                      <span>{getExtension(file.name).toUpperCase()}</span>
                    </div>
                  )}

                  <div className="privacy-strip">
                    <span>Local only</span>
                    <span>No upload</span>
                    <span>No server</span>
                    <span>No account</span>
                  </div>

                  <button
                    type="button"
                    className="button primary"
                    onClick={runExtract}
                    disabled={!file || busy}
                  >
                    {busy ? 'Working…' : 'Extract text'}
                  </button>
                </section>
              )}

              {step === 'process' && (
                <section className="browser-panel active">
                  <div className="panel-heading">
                    <h2>Clean and chunk</h2>
                    <p>
                      Chunks are the pieces an AI actually searches. Overlap keeps a sentence
                      from being lost when it falls across a boundary.
                    </p>
                  </div>

                  {!raw ? (
                    <p className="fine-print">Extract a file first.</p>
                  ) : (
                    <>
                      <div className="pipeline-grid">
                        <article className="is-done">
                          <strong>Extract</strong>
                          <p>Readable text pulled out of your file.</p>
                        </article>
                        <article>
                          <strong>Clean</strong>
                          <p>Spacing normalised, broken words rejoined.</p>
                        </article>
                        <article>
                          <strong>Chunk</strong>
                          <p>Split into overlapping pieces an AI can search.</p>
                        </article>
                        <article>
                          <strong>Protect</strong>
                          <p>Optional encryption before you move the file.</p>
                        </article>
                      </div>

                      <div className="artifact-panel">
                        <div>
                          <strong>Extracted text</strong>
                          <p>
                            {raw.text.length.toLocaleString()} characters
                            {raw.page_count ? ` · ${raw.page_count} pages` : ''}
                          </p>
                        </div>
                        <span className="badge">{raw.doc_id}</span>
                      </div>

                      <div className="text-preview">
                        <pre>{raw.text.slice(0, 1500)}</pre>
                      </div>

                      <div className="settings-row">
                        <label>
                          Chunk size (characters)
                          <input
                            type="number"
                            min={100}
                            max={4000}
                            value={chunkSize}
                            onChange={(e) => setChunkSize(Number(e.target.value))}
                          />
                        </label>
                        <label>
                          Chunk overlap (characters)
                          <input
                            type="number"
                            min={0}
                            max={1000}
                            value={chunkOverlap}
                            onChange={(e) => setChunkOverlap(Number(e.target.value))}
                          />
                        </label>
                      </div>

                      <div className="option-list">
                        <label>
                          <input
                            type="checkbox"
                            checked={encryptEnabled}
                            onChange={(e) => setEncryptEnabled(e.target.checked)}
                          />
                          <span>
                            <strong>Encrypt the result</strong>
                            <small>
                              RSA-2048 + AES-256-GCM, the same format as the desktop app — an
                              encrypted file made here opens there. You only need this if you
                              plan to move the file somewhere else.
                            </small>
                          </span>
                        </label>

                        <label>
                          <input
                            type="checkbox"
                            checked={persistEnabled}
                            onChange={(e) => setPersistEnabled(e.target.checked)}
                          />
                          <span>
                            <strong>Keep a copy in this browser</strong>
                            <small>
                              Off by default. Leave it off and everything disappears when you
                              close the tab — which is usually what you want.
                            </small>
                          </span>
                        </label>
                      </div>

                      <button
                        type="button"
                        className="button primary"
                        onClick={runChunk}
                        disabled={busy}
                      >
                        {busy ? 'Working…' : 'Create chunks'}
                      </button>
                    </>
                  )}
                </section>
              )}

              {step === 'artifacts' && (
                <section className="browser-panel active">
                  <div className="panel-heading">
                    <h2>Your artifacts</h2>
                    <p>
                      These files are identical in format to the desktop app's output, so they
                      load into AnythingLLM the same way.
                    </p>
                  </div>

                  {!chunks ? (
                    <p className="fine-print">Nothing produced yet.</p>
                  ) : (
                    <>
                      <div className="artifact-panel">
                        <div>
                          <strong>{chunks.total_chunks} chunks</strong>
                          <p>
                            {chunks.config.chunk_size} characters each,{' '}
                            {chunks.config.chunk_overlap} overlapping
                          </p>
                        </div>
                        <span className="badge">{chunks.doc_id}</span>
                      </div>

                      <div className="chunk-row">
                        {chunks.chunks.slice(0, 8).map((chunk) => (
                          <span key={chunk.chunk_id}>{chunk.chunk_id}</span>
                        ))}
                        {chunks.total_chunks > 8 && <span>+{chunks.total_chunks - 8} more</span>}
                      </div>

                      <div className="chunk-list">
                        {chunks.chunks.slice(0, 3).map((chunk) => (
                          <article key={chunk.chunk_id}>
                            <code>{chunk.chunk_id}</code>
                            <p>{chunk.text.slice(0, 260)}…</p>
                          </article>
                        ))}
                      </div>

                      <div className="button-row">
                        <button
                          type="button"
                          className="button primary"
                          onClick={() => downloadArtifact(chunks, chunkArtifactFilename(chunks))}
                        >
                          Download chunk JSON
                        </button>
                        {raw && (
                          <button
                            type="button"
                            className="button secondary"
                            onClick={() => downloadArtifact(raw, rawArtifactFilename(raw))}
                          >
                            Download raw JSON
                          </button>
                        )}
                        {encrypted && (
                          <button
                            type="button"
                            className="button secondary"
                            onClick={() => downloadBytes(encrypted.bytes, encrypted.filename)}
                          >
                            Download encrypted (.enc)
                          </button>
                        )}
                        {keyPair && (
                          <button type="button" className="button secondary" onClick={exportKeys}>
                            Export keypair
                          </button>
                        )}
                      </div>

                      {encrypted && (
                        <p className="fine-print">
                          The .enc file is unreadable without your private key. Export the
                          keypair before you close this tab, or you will not be able to open it
                          again — including with the desktop app.
                        </p>
                      )}

                      {!persistEnabled && (
                        <p className="fine-print">
                          Nothing is saved. Closing or refreshing this tab discards everything —
                          download what you want to keep.
                        </p>
                      )}
                    </>
                  )}

                  {saved.length > 0 && (
                    <>
                      <div className="panel-heading" style={{ marginTop: '2rem' }}>
                        <h3>Kept in this browser ({saved.length})</h3>
                        <p>Stored on this device only. Nothing was sent anywhere.</p>
                      </div>
                      <div className="chunk-list">
                        {saved.map((entry) => (
                          <article key={entry.doc_id}>
                            <code>{entry.doc_id}</code>
                            <p>
                              {entry.source_filename} · {entry.total_chunks} chunks ·{' '}
                              {new Date(entry.saved_at).toLocaleString()}
                            </p>
                            <div className="button-row">
                              <button
                                type="button"
                                className="button secondary"
                                onClick={() =>
                                  downloadArtifact(entry.chunks, chunkArtifactFilename(entry.chunks))
                                }
                              >
                                Download
                              </button>
                              <button
                                type="button"
                                className="button secondary"
                                onClick={async () => {
                                  await deleteArtifact(entry.doc_id);
                                  record('delete', 'artifact', entry.doc_id, 'allow', 'user_deleted');
                                  await refreshSaved();
                                }}
                              >
                                Delete
                              </button>
                            </div>
                          </article>
                        ))}
                      </div>
                      <button
                        type="button"
                        className="button secondary"
                        onClick={async () => {
                          await clearAll();
                          record('clear', 'storage', 'all', 'allow', 'user_cleared_all');
                          await refreshSaved();
                        }}
                      >
                        Erase everything kept in this browser
                      </button>
                    </>
                  )}
                </section>
              )}

                            <div hidden={step !== 'assistant'}>
                <Assistant chunks={chunks} />
              </div>

              {step === 'audit' && (
                <section className="browser-panel active">
                  <div className="panel-heading">
                    <h2>What happened</h2>
                    <p>
                      Every action this page took, and why. The same record the desktop app's
                      permission layer keeps — except here you can actually read it.
                    </p>
                  </div>

                  <div className="text-preview">
                    {audit.length === 0 ? (
                      <p className="fine-print">Nothing yet.</p>
                    ) : (
                      <table className="audit-table">
                        <thead>
                          <tr>
                            <th>Time</th>
                            <th>Action</th>
                            <th>Resource</th>
                            <th>Decision</th>
                            <th>Reason</th>
                          </tr>
                        </thead>
                        <tbody>
                          {audit.map((entry, index) => (
                            <tr key={`${entry.ts_utc}-${index}`}>
                              <td>{new Date(entry.ts_utc).toLocaleTimeString()}</td>
                              <td>{entry.action}</td>
                              <td title={entry.resource_id}>{entry.resource_id}</td>
                              <td className={entry.decision === 'deny' ? 'is-deny' : 'is-allow'}>
                                {entry.decision}
                              </td>
                              <td>{entry.reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  <div className="button-row">
                    <button
                      type="button"
                      className="button secondary"
                      onClick={() => downloadText(exportAuditJson(), 'ppllm_audit_log.json')}
                      disabled={audit.length === 0}
                    >
                      Export log
                    </button>
                    <button
                      type="button"
                      className="button secondary"
                      onClick={() => clearEntries()}
                      disabled={audit.length === 0}
                    >
                      Clear log
                    </button>
                  </div>
                </section>
              )}
            </div>
          </div>
        </div>
      </div>

      {pendingSensitive && (
        <div className="source-modal" role="dialog" aria-modal="true">
          <div className="source-modal-card">
            <h3>This file may be sensitive</h3>
            <p>
              <strong>{pendingSensitive.name}</strong> contains{' '}
              {matchedKeywords(pendingSensitive.name)
                .map((k) => `"${k}"`)
                .join(', ')}
              . Continue?
            </p>
            <p className="fine-print">
              This check only reads the file's name, never its contents — so it will miss a
              sensitive file that happens to be named something ordinary.
            </p>
            <div className="button-row">
              <button
                type="button"
                className="button primary"
                onClick={() => {
                  record(
                    'consent',
                    'sensitive_file',
                    pendingSensitive.name,
                    'allow',
                    'user_confirmed_at_prompt'
                  );
                  acceptFile(pendingSensitive);
                  setPendingSensitive(null);
                }}
              >
                Yes, continue
              </button>
              <button
                type="button"
                className="button secondary"
                onClick={() => {
                  record(
                    'consent',
                    'sensitive_file',
                    pendingSensitive.name,
                    'deny',
                    'user_denied_at_prompt'
                  );
                  setPendingSensitive(null);
                  if (fileInput.current) fileInput.current.value = '';
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
