import type { ChunkArtifact, ChunkOptions, RawArtifact } from '../core/types';
import type { PipelineStage, WorkerRequest, WorkerResponse } from './protocol';

/**
 * Main-thread client for the pipeline worker.
 *
 * One worker is created lazily and reused. Requests are correlated by id so a
 * stale response from an abandoned run can never be mistaken for the current one.
 */

let worker: Worker | null = null;
let nextId = 0;

function getWorker(): Worker {
  worker ??= new Worker(new URL('./pipeline.worker.ts', import.meta.url), { type: 'module' });
  return worker;
}

export interface ProcessCallbacks {
  onProgress?: (stage: PipelineStage, note: string) => void;
}

export function processInWorker(
  doc: RawArtifact,
  options: ChunkOptions,
  callbacks: ProcessCallbacks = {}
): Promise<ChunkArtifact> {
  const id = `req-${(nextId += 1)}`;
  const activeWorker = getWorker();

  return new Promise<ChunkArtifact>((resolve, reject) => {
    const handleMessage = (event: MessageEvent<WorkerResponse>) => {
      const response = event.data;
      // Ignore anything belonging to a previous request.
      if (response.id !== id) return;

      switch (response.type) {
        case 'progress':
          callbacks.onProgress?.(response.stage, response.note);
          break;
        case 'done':
          cleanup();
          resolve(response.artifact);
          break;
        case 'error':
          cleanup();
          reject(new Error(response.message));
          break;
      }
    };

    const handleError = (event: ErrorEvent) => {
      cleanup();
      reject(new Error(event.message || 'Pipeline worker failed'));
    };

    function cleanup() {
      activeWorker.removeEventListener('message', handleMessage);
      activeWorker.removeEventListener('error', handleError);
    }

    activeWorker.addEventListener('message', handleMessage);
    activeWorker.addEventListener('error', handleError);

    const request: WorkerRequest = { id, type: 'process', doc, options };
    activeWorker.postMessage(request);
  });
}
