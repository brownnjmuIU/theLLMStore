import { chunkText } from './chunker';
import { cleanText } from './cleaner';
import { DEFAULT_CHUNK_OPTIONS, type ChunkArtifact, type ChunkOptions, type RawArtifact } from './types';

/**
 * Port of processing/pipeline.py::process_document.
 *
 * Deliberately a different signature from Python's. The Python version takes a
 * FILE PATH and loads from disk, which couples the pipeline to storage and is why
 * it has never been unit-testable. There are no paths in a browser, so this takes
 * the artifact directly and stays pure: no I/O, no DOM, no side effects.
 *
 * Persistence and encryption happen at the edges — src/storage/ and src/crypto/ —
 * not here. The same refactor is worth making in Python (CLAUDE.md 10.4).
 */
export function processDocument(
  doc: RawArtifact,
  options: ChunkOptions = DEFAULT_CHUNK_OPTIONS
): ChunkArtifact {
  const cleaned = cleanText(doc.text);
  return chunkText(cleaned, doc.doc_id, doc.source_filename, doc.file_type, options);
}
