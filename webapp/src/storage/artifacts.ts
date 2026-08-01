import { generateDocId } from '../core/docId';
import type { ChunkArtifact, ExtractionResult, RawArtifact } from '../core/types';

/**
 * Artifact construction and saving.
 *
 * Session-only by design: nothing is written to browser storage in Phase 1, so a
 * refresh genuinely loses everything. Opt-in persistence (IndexedDB, with a
 * visible clear-all) is Phase 2. See CLAUDE.md section 10.1.
 */

/** Mirrors storage/json_store.py::save_artifact, minus the disk write. */
export async function buildRawArtifact(
  filename: string,
  fileType: string,
  extraction: ExtractionResult
): Promise<RawArtifact> {
  return {
    doc_id: await generateDocId(filename, extraction.text),
    source_filename: filename,
    file_type: fileType,
    ingested_at: new Date().toISOString(),
    page_count: extraction.page_count,
    text: extraction.text,
  };
}

/** Matches the Python file naming so outputs are interchangeable. */
export function rawArtifactFilename(artifact: RawArtifact): string {
  return `doc_${artifact.doc_id}.json`;
}

export function chunkArtifactFilename(artifact: ChunkArtifact): string {
  return `doc_${artifact.doc_id}_chunks.json`;
}

/**
 * Serialise exactly as Python does: indent=2, ensure_ascii=False.
 * Non-ASCII text stays readable rather than becoming \\uXXXX escapes.
 */
export function serialiseArtifact(artifact: RawArtifact | ChunkArtifact): string {
  return JSON.stringify(artifact, null, 2);
}

/**
 * Save via the standard download mechanism.
 *
 * Deliberately not the File System Access API: that is Chrome/Edge only, and
 * supporting Safari and Firefox is a locked requirement. A "save to folder"
 * enhancement can layer on top later where the browser offers it.
 */
function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);

  // Revoke on the next tick — revoking synchronously can cancel the download
  // in some browsers before it starts.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function downloadArtifact(artifact: RawArtifact | ChunkArtifact, filename: string): void {
  saveBlob(new Blob([serialiseArtifact(artifact)], { type: 'application/json' }), filename);
}

/** For encrypted .enc bundles. */
export function downloadBytes(bytes: Uint8Array, filename: string): void {
  saveBlob(new Blob([bytes as BlobPart], { type: 'application/octet-stream' }), filename);
}

/** For PEM keys and the exported audit log. */
export function downloadText(text: string, filename: string): void {
  saveBlob(new Blob([text], { type: 'text/plain' }), filename);
}
