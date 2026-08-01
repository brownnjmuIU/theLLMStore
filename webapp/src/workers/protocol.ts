import type { ChunkArtifact, ChunkOptions, RawArtifact } from '../core/types';

/**
 * Typed message protocol between the UI and the pipeline worker.
 *
 * Hand-written rather than using Comlink: the surface is two messages wide, and
 * a plain discriminated union stays readable for whoever inherits this.
 */

export interface ProcessRequest {
  id: string;
  type: 'process';
  doc: RawArtifact;
  options: ChunkOptions;
}

export type WorkerRequest = ProcessRequest;

export type PipelineStage = 'cleaning' | 'chunking' | 'done';

export type WorkerResponse =
  | { id: string; type: 'progress'; stage: PipelineStage; note: string }
  | { id: string; type: 'done'; artifact: ChunkArtifact }
  | { id: string; type: 'error'; message: string };
