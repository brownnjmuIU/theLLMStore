/**
 * The data contract.
 *
 * These shapes must match the Python implementation EXACTLY, including
 * snake_case field names — the JSON produced here has to be interchangeable
 * with the JSON produced by the desktop app, and loadable by AnythingLLM.
 *
 * Python sources of truth:
 *   storage/json_store.py::save_artifact   -> RawArtifact
 *   processing/chunker.py::chunk_text      -> ChunkArtifact
 *   extractors/*.py                        -> ExtractionResult
 */

/** One extractor's output. Mirrors `{"text": ..., "page_count": ...}` in Python. */
export interface ExtractionResult {
  text: string;
  /** Pages for PDF/PPTX; null for formats without pagination (DOCX, images, JSON). */
  page_count: number | null;
  /** Extractors may attach extras: ocr_text, transcript_text, cookie_records. */
  [key: string]: unknown;
}

/** Stage 3 output — extracted text plus provenance, before cleaning. */
export interface RawArtifact {
  doc_id: string;
  source_filename: string;
  file_type: string;
  /** ISO-8601 UTC. */
  ingested_at: string;
  page_count: number | null;
  text: string;
}

export interface Chunk {
  /** `${doc_id}_${index padded to 4}` — e.g. "3772bc03_0001". */
  chunk_id: string;
  /** 1-based. */
  chunk_index: number;
  /**
   * WARNING: in the Python implementation these are RECONSTRUCTED by
   * accumulating lengths and subtracting overlap, not measured. They drift
   * monotonically — verified at roughly -52 chars per boundary on fixture 001.
   * They cannot be used to locate text in the source. See CLAUDE.md section 6.
   */
  char_start: number;
  char_end: number;
  text: string;
}

export interface ChunkConfig {
  chunk_size: number;
  chunk_overlap: number;
  splitter: string;
}

/** Stage 4 output — the deliverable that gets loaded into a RAG tool. */
export interface ChunkArtifact {
  doc_id: string;
  source_filename: string;
  file_type: string;
  total_chunks: number;
  /**
   * ISO-8601 UTC. Optional here because conformance fixtures strip it —
   * `datetime.now()` is non-deterministic and cannot live in a golden file.
   */
  chunked_at?: string;
  config: ChunkConfig;
  chunks: Chunk[];
}

export interface ChunkOptions {
  chunk_size: number;
  chunk_overlap: number;
}

export const DEFAULT_CHUNK_OPTIONS: ChunkOptions = {
  chunk_size: 800,
  chunk_overlap: 100,
};

/**
 * Separator ladder, most semantically meaningful first. Must match
 * processing/chunker.py exactly — changing the order changes every boundary.
 */
export const SEPARATORS: readonly string[] = ['\n\n', '\n', '. ', ', ', ' ', ''];

export const SPLITTER_NAME = 'RecursiveCharacterTextSplitter';
