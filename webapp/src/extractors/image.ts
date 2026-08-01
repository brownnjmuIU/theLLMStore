import type { ExtractionResult } from '../core/types';

/**
 * Port of extractors/image_extractor.py.
 *
 * Target is the WINDOWS desktop build, which ships Tesseract via
 * `choco install tesseract` and therefore produces real OCR text. Matching a Mac
 * without Tesseract (which yields "[No OCR text detected]") would be matching a
 * broken configuration, not the software.
 *
 * Output line order is reproduced exactly:
 *
 *     Image File
 *     Format: PNG
 *     Mode: RGB
 *     Size: 900x300
 *                          <- blank, only when EXIF is present
 *     EXIF Metadata:
 *     Make: Apple
 *     ...
 *                          <- blank
 *     OCR Text:
 *     <text, or [No OCR text detected]>
 *
 * Format/Mode/Size are read from the file header rather than a canvas, because a
 * canvas always reports RGBA and PIL reports the file's real colour mode.
 *
 * All Tesseract assets are served same-origin (see scripts/vendor-tesseract.mjs).
 * tesseract.js would otherwise fetch them from cdn.jsdelivr.net, which would break
 * the local-only guarantee.
 */

interface HeaderInfo {
  format: string;
  mode: string;
  width: number;
  height: number;
}

/** PNG colour type -> PIL mode. */
function pngMode(colorType: number, bitDepth: number): string {
  switch (colorType) {
    case 0:
      return bitDepth === 1 ? '1' : 'L';
    case 2:
      return 'RGB';
    case 3:
      return 'P';
    case 4:
      return 'LA';
    case 6:
      return 'RGBA';
    default:
      return 'RGB';
  }
}

/** JPEG component count -> PIL mode. */
function jpegMode(components: number): string {
  if (components === 1) return 'L';
  if (components === 4) return 'CMYK';
  return 'RGB';
}

function readHeader(bytes: Uint8Array): HeaderInfo | null {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);

  // PNG: 8-byte signature, then IHDR at offset 16.
  if (
    bytes.length > 24 &&
    bytes[0] === 0x89 &&
    bytes[1] === 0x50 &&
    bytes[2] === 0x4e &&
    bytes[3] === 0x47
  ) {
    return {
      format: 'PNG',
      width: view.getUint32(16, false),
      height: view.getUint32(20, false),
      mode: pngMode(bytes[25] ?? 2, bytes[24] ?? 8),
    };
  }

  // JPEG: walk the marker segments to the Start Of Frame.
  if (bytes.length > 4 && bytes[0] === 0xff && bytes[1] === 0xd8) {
    let offset = 2;
    while (offset + 9 < bytes.length) {
      if (bytes[offset] !== 0xff) {
        offset += 1;
        continue;
      }
      const marker = bytes[offset + 1] ?? 0;
      // SOF0-SOF15, excluding DHT (c4), JPG (c8) and DAC (cc).
      if (marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc) {
        return {
          format: 'JPEG',
          height: view.getUint16(offset + 5, false),
          width: view.getUint16(offset + 7, false),
          mode: jpegMode(bytes[offset + 9] ?? 3),
        };
      }
      offset += 2 + view.getUint16(offset + 2, false);
    }
  }

  return null;
}

/**
 * Does the file contain a genuine EXIF block?
 *
 * This gate matters for parity. PIL's getexif() returns ONLY the TIFF/EXIF IFD,
 * so a PNG with no eXIf chunk yields nothing and the Python extractor emits no
 * EXIF section at all. exifr, left to itself, also reports PNG structural fields
 * (BitDepth, ColorType, Interlace) — which would add an EXIF block the desktop
 * app never produces.
 */
function hasExifBlock(bytes: Uint8Array): boolean {
  // JPEG: an APP1 segment introduced by "Exif\0\0".
  if (bytes[0] === 0xff && bytes[1] === 0xd8) {
    for (let i = 2; i + 10 < bytes.length && i < 65536; i += 1) {
      if (bytes[i] === 0xff && bytes[i + 1] === 0xe1) {
        return (
          bytes[i + 4] === 0x45 && // E
          bytes[i + 5] === 0x78 && // x
          bytes[i + 6] === 0x69 && // i
          bytes[i + 7] === 0x66 //   f
        );
      }
    }
    return false;
  }

  // PNG: an "eXIf" chunk.
  if (bytes[0] === 0x89 && bytes[1] === 0x50) {
    for (let i = 8; i + 4 < bytes.length; i += 1) {
      if (
        bytes[i] === 0x65 && // e
        bytes[i + 1] === 0x58 && // X
        bytes[i + 2] === 0x49 && // I
        bytes[i + 3] === 0x66 //    f
      ) {
        return true;
      }
    }
  }

  return false;
}

/** Read EXIF tags, named as PIL's ExifTags.TAGS names them. */
async function readExif(bytes: Uint8Array): Promise<Record<string, unknown> | null> {
  if (!hasExifBlock(bytes)) return null;

  try {
    const exifr = await import('exifr');
    const parsed = (await exifr.parse(bytes as unknown as ArrayBuffer, {
      tiff: true,
      exif: true,
      gps: true,
      translateKeys: true,
      translateValues: false,
      reviveValues: false,
    })) as Record<string, unknown> | undefined;

    if (!parsed || Object.keys(parsed).length === 0) return null;
    return parsed;
  } catch {
    // EXIF is optional metadata; never fail the extraction over it.
    return null;
  }
}

export interface OcrPaths {
  workerPath?: string;
  corePath?: string;
  langPath?: string;
}

/** Same-origin asset locations. BASE_URL is '/studio/' in this deployment. */
function defaultOcrPaths(): OcrPaths {
  const base = import.meta.env.BASE_URL || '/';
  return {
    workerPath: `${base}tesseract/worker.min.js`,
    corePath: `${base}tesseract/tesseract-core-simd-lstm.wasm.js`,
    langPath: base + 'tesseract',
  };
}

async function runOcr(
  bytes: Uint8Array,
  paths: OcrPaths
): Promise<{ text: string; error: string | null }> {
  try {
    const { createWorker } = await import('tesseract.js');
    const worker = await createWorker('eng', 1, {
      ...paths,
      // Our vendored eng.traineddata is uncompressed; tesseract.js expects .gz
      // unless told otherwise.
      gzip: false,
      legacyCore: false,
      legacyLang: false,
    });

    try {
      // tesseract.js accepts different inputs per environment: a Blob in the
      // browser, a Buffer under Node. Detecting Buffer keeps one code path
      // working in the app, in a Web Worker, and in conformance tests.
      const nodeBuffer = (globalThis as { Buffer?: { from(data: Uint8Array): unknown } }).Buffer;
      const input = nodeBuffer
        ? nodeBuffer.from(bytes)
        : new Blob([bytes as BlobPart], { type: 'application/octet-stream' });

      const { data } = await worker.recognize(input as Parameters<typeof worker.recognize>[0]);
      return { text: data.text ?? '', error: null };
    } finally {
      await worker.terminate();
    }
  } catch (error) {
    // Mirrors the Python extractor, which catches and reports rather than raising.
    return { text: '', error: error instanceof Error ? error.message : String(error) };
  }
}

export async function extractTextFromImage(
  fileBytes: Uint8Array,
  ocrPaths: OcrPaths = defaultOcrPaths()
): Promise<ExtractionResult> {
  const lines: string[] = ['Image File'];

  const header = readHeader(fileBytes);
  lines.push(`Format: ${header?.format ?? 'None'}`);
  lines.push(`Mode: ${header?.mode ?? 'None'}`);
  lines.push(`Size: ${header?.width ?? 0}x${header?.height ?? 0}`);

  const exif = await readExif(fileBytes);
  if (exif) {
    lines.push('');
    lines.push('EXIF Metadata:');
    for (const [tag, value] of Object.entries(exif)) {
      lines.push(`${tag}: ${String(value)}`);
    }
  }

  const ocr = await runOcr(fileBytes, ocrPaths);
  const trimmed = ocr.text.trim();

  lines.push('');
  lines.push('OCR Text:');
  lines.push(trimmed || '[No OCR text detected]');
  if (ocr.error) lines.push(`OCR Error: ${ocr.error}`);

  return {
    text: lines.join('\n').trim(),
    page_count: null,
    ocr_text: trimmed,
  };
}
