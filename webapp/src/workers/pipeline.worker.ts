/// <reference lib="webworker" />
import { chunkText } from '../core/chunker';
import { cleanText } from '../core/cleaner';
import type { WorkerRequest, WorkerResponse } from './protocol';

/**
 * Cleaning and chunking, off the main thread.
 *
 * This is the CPU-bound, pure part of the pipeline — exactly what the desktop app
 * runs on its UI thread, papering over the freeze with
 * QApplication.processEvents(). Not inheriting that.
 *
 * Extraction deliberately stays on the main thread for now:
 *   - pdf.js already offloads parsing to its own worker, so PDFs never block
 *   - running it here would mean a nested worker, which is supported but is the
 *     first thing to break in Safari
 * If profiling shows large DOCX files blocking, move extraction here and accept
 * the nesting.
 */

const ctx = self as unknown as DedicatedWorkerGlobalScope;

function post(message: WorkerResponse): void {
  ctx.postMessage(message);
}

ctx.addEventListener('message', (event: MessageEvent<WorkerRequest>) => {
  const request = event.data;
  if (request.type !== 'process') return;

  try {
    post({ id: request.id, type: 'progress', stage: 'cleaning', note: 'Normalising text' });
    const cleaned = cleanText(request.doc.text);

    post({ id: request.id, type: 'progress', stage: 'chunking', note: 'Splitting into chunks' });
    const artifact = chunkText(
      cleaned,
      request.doc.doc_id,
      request.doc.source_filename,
      request.doc.file_type,
      request.options
    );

    post({ id: request.id, type: 'done', artifact });
  } catch (error) {
    post({
      id: request.id,
      type: 'error',
      message: error instanceof Error ? error.message : String(error),
    });
  }
});
