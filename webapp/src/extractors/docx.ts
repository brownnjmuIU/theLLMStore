import type { ExtractionResult } from '../core/types';

/**
 * Port of extractors/docs_extractor.py, using mammoth in place of python-docx.
 *
 * Python iterates doc.paragraphs, skips empty ones, and joins with "\n\n".
 * Mammoth's extractRawText joins paragraphs with a single "\n", so we re-split
 * and re-join to match Python's paragraph separation.
 *
 * Shares python-docx's limitation deliberately: body paragraphs only. Table
 * cells, headers, footers, footnotes and text boxes are NOT extracted. Matching
 * the desktop app matters more here than extracting more — a browser version
 * that silently returned different content would undermine the whole comparison.
 *
 * page_count is null because DOCX has no fixed pagination.
 */
export async function extractTextFromDocx(fileBytes: Uint8Array): Promise<ExtractionResult> {
  const mammoth = await import('mammoth');

  // mammoth ships two builds with different input contracts: the browser build
  // takes { arrayBuffer }, the Node build only accepts { buffer | path | file }.
  // Detecting Buffer rather than branching on a bundler flag keeps this working
  // in the browser, in Node conformance tests, and in a Web Worker alike.
  const nodeBuffer = (globalThis as { Buffer?: { from(data: Uint8Array): unknown } }).Buffer;

  const input = nodeBuffer
    ? { buffer: nodeBuffer.from(fileBytes) }
    : {
        // Slice to drop any Uint8Array view offset — mammoth needs the exact bytes.
        arrayBuffer: fileBytes.buffer.slice(
          fileBytes.byteOffset,
          fileBytes.byteOffset + fileBytes.byteLength
        ) as ArrayBuffer,
      };

  const result = await mammoth.extractRawText(
    input as Parameters<typeof mammoth.extractRawText>[0]
  );

  const paragraphs = result.value
    .split('\n')
    .filter((paragraph) => paragraph.trim() !== '');

  return {
    text: paragraphs.join('\n\n').trim(),
    page_count: null,
  };
}
