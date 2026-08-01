import type { ExtractionResult } from '../core/types';

/**
 * Extractor dispatch — the browser equivalent of the if/elif chain in
 * desktop_app.py lines 524-543 and process_aggregator_manifest.py.
 *
 * Every extractor is dynamically imported so a user who only opens PDFs never
 * downloads the DOCX or OCR code. That is what keeps the initial bundle under
 * the 250 KB budget.
 */

/** Implemented in Phase 1. */
export const SUPPORTED_EXTENSIONS = ['pdf', 'docx', 'pptx', 'jpg', 'jpeg', 'png', 'json'] as const;

/**
 * Recognised but not implemented, so the UI can say "not yet" rather than
 * "unsupported" — different messages to a user.
 */
export const PLANNED_EXTENSIONS = ['sqlite', 'db'] as const;

/** Desktop-only. Whisper in WASM means a 40-75 MB model download; out of scope. */
export const DESKTOP_ONLY_EXTENSIONS = ['mp4', 'mov'] as const;

export type SupportedExtension = (typeof SUPPORTED_EXTENSIONS)[number];

export class UnsupportedFileTypeError extends Error {
  constructor(
    public readonly extension: string,
    public readonly reason: 'planned' | 'desktop-only' | 'unknown'
  ) {
    super(
      reason === 'planned'
        ? `.${extension} files are not supported yet — coming in a later release.`
        : reason === 'desktop-only'
          ? `.${extension} files are only supported in the desktop app. Video transcription needs a large local model that is impractical to download in a browser.`
          : `.${extension} files are not supported.`
    );
    this.name = 'UnsupportedFileTypeError';
  }
}

export function getExtension(filename: string): string {
  const dot = filename.lastIndexOf('.');
  return dot === -1 ? '' : filename.slice(dot + 1).toLowerCase();
}

export function isSupported(filename: string): boolean {
  return (SUPPORTED_EXTENSIONS as readonly string[]).includes(getExtension(filename));
}

export async function extractFromFile(
  filename: string,
  fileBytes: Uint8Array
): Promise<ExtractionResult> {
  const extension = getExtension(filename);

  switch (extension) {
    case 'pdf': {
      const { extractTextFromPdf } = await import('./pdf');
      return extractTextFromPdf(fileBytes);
    }
    case 'docx': {
      const { extractTextFromDocx } = await import('./docx');
      return extractTextFromDocx(fileBytes);
    }
    case 'pptx': {
      const { extractTextFromPptx } = await import('./pptx');
      return extractTextFromPptx(fileBytes);
    }
    case 'jpg':
    case 'jpeg':
    case 'png': {
      const { extractTextFromImage } = await import('./image');
      return extractTextFromImage(fileBytes);
    }
    case 'json': {
      const { extractTextFromPlatformExport } = await import('./platform');
      return extractTextFromPlatformExport(fileBytes);
    }
    default: {
      if ((DESKTOP_ONLY_EXTENSIONS as readonly string[]).includes(extension)) {
        throw new UnsupportedFileTypeError(extension, 'desktop-only');
      }
      if ((PLANNED_EXTENSIONS as readonly string[]).includes(extension)) {
        throw new UnsupportedFileTypeError(extension, 'planned');
      }
      throw new UnsupportedFileTypeError(extension || '(none)', 'unknown');
    }
  }
}
