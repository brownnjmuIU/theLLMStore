import { pyStrip } from './pythonCompat';
import {
  DEFAULT_CHUNK_OPTIONS,
  SEPARATORS,
  SPLITTER_NAME,
  type Chunk,
  type ChunkArtifact,
  type ChunkOptions,
} from './types';
import { codePointLength } from './unicode';

/**
 * Port of processing/chunker.py::chunk_text, including a faithful reimplementation
 * of LangChain's RecursiveCharacterTextSplitter.
 *
 * Hand-ported rather than depending on @langchain/textsplitters: betting Tier 1
 * conformance on a JS library matching a Python library's exact behaviour is a bet
 * that eventually loses. See CLAUDE.md section 10.3.
 *
 * Mirrors these LangChain defaults, which the Python side relies on:
 *   keep_separator  = true   -> separators are PREPENDED to the following split,
 *                              and merging joins with "" rather than the separator
 *   strip_whitespace = true  -> each joined chunk is str.strip()'d
 *   is_separator_regex = false -> separators are literal, so splitting uses
 *                              indexOf rather than a regex (avoids escaping bugs
 *                              entirely and is exactly equivalent)
 *   length_function = len    -> CODE POINTS, not UTF-16 units
 */

/**
 * Equivalent of Python's `re.split(f"({separator})", text)` for a literal separator:
 * returns [before, sep, after, sep, after, ...].
 *
 * Uses indexOf on UTF-16 indices, which is safe because we only ever cut at
 * separator boundaries and every separator in the ladder is ASCII.
 */
function splitWithSeparatorCaptured(text: string, separator: string): string[] {
  const parts: string[] = [];
  let start = 0;
  let index = text.indexOf(separator, start);

  while (index !== -1) {
    parts.push(text.slice(start, index));
    parts.push(separator);
    start = index + separator.length;
    index = text.indexOf(separator, start);
  }
  parts.push(text.slice(start));
  return parts;
}

/** Port of langchain's _split_text_with_regex with keep_separator=True. */
function splitTextWithSeparator(text: string, separator: string): string[] {
  let splits: string[];

  if (separator !== '') {
    const raw = splitWithSeparatorCaptured(text, separator);

    // Recombine so each separator is prepended to the text that follows it.
    const merged: string[] = [];
    for (let i = 1; i < raw.length; i += 2) {
      merged.push((raw[i] ?? '') + (raw[i + 1] ?? ''));
    }
    if (raw.length % 2 === 0) {
      const last = raw[raw.length - 1];
      if (last !== undefined) merged.push(last);
    }
    splits = [raw[0] ?? '', ...merged];
  } else {
    // Empty separator: split into individual characters. Python's list(text)
    // yields CODE POINTS, so Array.from is required — [...text] would be wrong
    // only if it split surrogate pairs, which it does not, but .split('') would.
    splits = Array.from(text);
  }

  return splits.filter((s) => s !== '');
}

/** Port of langchain's _join_docs. Returns null for an empty result. */
function joinDocs(docs: string[], separator: string): string | null {
  const text = pyStrip(docs.join(separator));
  return text === '' ? null : text;
}

/**
 * Port of langchain's _merge_splits.
 *
 * Packs adjacent splits up toward chunkSize, then pops from the front until the
 * carried-over tail is within chunkOverlap. This is where overlap actually happens
 * — and why overlap is a CEILING rather than a guarantee.
 */
function mergeSplits(
  splits: string[],
  separator: string,
  chunkSize: number,
  chunkOverlap: number
): string[] {
  const separatorLen = codePointLength(separator);
  const docs: string[] = [];
  let currentDoc: string[] = [];
  let total = 0;

  for (const d of splits) {
    const len = codePointLength(d);

    if (total + len + (currentDoc.length > 0 ? separatorLen : 0) > chunkSize) {
      if (currentDoc.length > 0) {
        const doc = joinDocs(currentDoc, separator);
        if (doc !== null) docs.push(doc);

        // Pop from the front while we are still carrying more than the overlap,
        // or while the incoming split still would not fit.
        // The length guard is defensive: Python would raise IndexError here, and
        // the arithmetic guarantees termination before that, but strict TS needs it.
        while (
          currentDoc.length > 0 &&
          (total > chunkOverlap ||
            (total + len + (currentDoc.length > 0 ? separatorLen : 0) > chunkSize && total > 0))
        ) {
          total -=
            codePointLength(currentDoc[0] ?? '') + (currentDoc.length > 1 ? separatorLen : 0);
          currentDoc = currentDoc.slice(1);
        }
      }
    }

    currentDoc.push(d);
    total += len + (currentDoc.length > 1 ? separatorLen : 0);
  }

  const doc = joinDocs(currentDoc, separator);
  if (doc !== null) docs.push(doc);
  return docs;
}

/**
 * Port of langchain's recursive _split_text.
 *
 * Walks the separator ladder: use the first separator present in the text, split
 * on it, and recurse into any piece still larger than chunkSize using the
 * remaining separators. The final '' separator is the hard character-level cut.
 */
function splitTextRecursive(
  text: string,
  separators: readonly string[],
  chunkSize: number,
  chunkOverlap: number
): string[] {
  const finalChunks: string[] = [];

  // Pick the first separator that appears in this text.
  let separator = separators[separators.length - 1] ?? '';
  let newSeparators: readonly string[] = [];

  for (let i = 0; i < separators.length; i += 1) {
    const candidate = separators[i] ?? '';
    if (candidate === '') {
      separator = candidate;
      break;
    }
    if (text.includes(candidate)) {
      separator = candidate;
      newSeparators = separators.slice(i + 1);
      break;
    }
  }

  const splits = splitTextWithSeparator(text, separator);

  // keep_separator=true means merging joins with "" — the separator is already
  // carried inside each split.
  const mergeSeparator = '';
  let goodSplits: string[] = [];

  for (const s of splits) {
    if (codePointLength(s) < chunkSize) {
      goodSplits.push(s);
    } else {
      if (goodSplits.length > 0) {
        finalChunks.push(...mergeSplits(goodSplits, mergeSeparator, chunkSize, chunkOverlap));
        goodSplits = [];
      }
      if (newSeparators.length === 0) {
        finalChunks.push(s);
      } else {
        finalChunks.push(...splitTextRecursive(s, newSeparators, chunkSize, chunkOverlap));
      }
    }
  }

  if (goodSplits.length > 0) {
    finalChunks.push(...mergeSplits(goodSplits, mergeSeparator, chunkSize, chunkOverlap));
  }

  return finalChunks;
}

/** The splitter itself, exported for testing and reuse. */
export function splitText(text: string, chunkSize: number, chunkOverlap: number): string[] {
  return splitTextRecursive(text, SEPARATORS, chunkSize, chunkOverlap);
}

/**
 * Port of processing/chunker.py::chunk_text.
 *
 * NOTE ON char_start / char_end: these reproduce Python's arithmetic, which is
 * WRONG. Offsets are reconstructed by accumulating lengths and subtracting overlap
 * rather than measured, so they drift monotonically — around -52 characters per
 * boundary, verified on conformance fixture 001. They cannot be used to locate
 * text in the source document.
 *
 * Reproduced deliberately so Tier 1 conformance passes. Fixing this is a separate,
 * deliberate change that must land in Python and TypeScript together, or the two
 * implementations silently diverge. See CLAUDE.md sections 6 and 10.10.
 */
export function chunkText(
  text: string,
  docId: string,
  sourceFilename: string,
  fileType: string,
  options: ChunkOptions = DEFAULT_CHUNK_OPTIONS
): ChunkArtifact {
  const { chunk_size: chunkSize, chunk_overlap: chunkOverlap } = options;

  const pieces = splitText(text, chunkSize, chunkOverlap);

  const chunks: Chunk[] = [];
  let currentPos = 0;

  pieces.forEach((piece, i) => {
    const chunkStart = currentPos;
    const chunkEnd = chunkStart + codePointLength(piece);

    chunks.push({
      chunk_id: `${docId}_${String(i + 1).padStart(4, '0')}`,
      chunk_index: i + 1,
      char_start: chunkStart,
      char_end: chunkEnd,
      text: piece,
    });

    currentPos = Math.max(0, chunkEnd - chunkOverlap);
  });

  return {
    doc_id: docId,
    source_filename: sourceFilename,
    file_type: fileType,
    total_chunks: pieces.length,
    chunked_at: new Date().toISOString(),
    config: {
      chunk_size: chunkSize,
      chunk_overlap: chunkOverlap,
      splitter: SPLITTER_NAME,
    },
    chunks,
  };
}
