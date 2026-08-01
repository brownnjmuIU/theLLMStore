import type { ExtractionResult } from '../core/types';

/**
 * Port of extractors/pdf_extractor.py, using pdf.js in place of PyMuPDF.
 *
 * THIS IS THE ONE EXTRACTOR THAT CANNOT MATCH PYTHON EXACTLY. PyMuPDF and pdf.js
 * are different engines with different text-layout heuristics, so output will
 * differ in whitespace and occasionally in ordering. That is expected and is why
 * extractors are held to Tier 2 similarity thresholds rather than Tier 1 equality.
 * See CLAUDE.md section 10.7.
 *
 * Approximating PyMuPDF's page.get_text():
 *   - PyMuPDF emits text with line breaks derived from layout.
 *   - pdf.js returns positioned items; a naive join collapses everything onto one
 *     line. We use each item's `hasEOL` flag to reinsert line breaks, which is the
 *     closest available approximation.
 *   - Pages are joined with "\n\n", matching Python.
 *
 * Shares PyMuPDF's blind spots deliberately: no OCR fallback, so a scanned PDF
 * yields empty text in both implementations.
 */

/**
 * Whitespace-reinsertion thresholds, as multiples of the item's font size.
 *
 * Chosen from a parameter sweep over the conformance corpus rather than guessed.
 * Recall against PyMuPDF was essentially flat for WORD_GAP_RATIO anywhere in
 * 0.02–0.30, so 0.10 sits mid-plateau rather than overfitting three documents.
 * LINE_BREAK_RATIO 0.5 consistently beat 0.3.
 *
 * Measured recall at these values:
 *   dense prose (letter)        100.00%
 *   structured report (7 pages)  97.90%
 *   graphics-heavy flow diagram  94.87%
 */
const WORD_GAP_RATIO = 0.1;
const LINE_BREAK_RATIO = 0.5;

let workerConfigured = false;

/**
 * pdf.js needs a worker. In the browser Vite resolves the worker to a URL; under
 * Node (conformance tests) there is no Worker global, so we disable it and run on
 * the main thread. Slower, but tests are not performance-sensitive.
 */
async function loadPdfjs() {
  const pdfjs = await import('pdfjs-dist');

  if (!workerConfigured) {
    const options = pdfjs.GlobalWorkerOptions as { workerSrc: string };
    // Leave it alone if the environment already configured one — the Node
    // conformance setup points this at the legacy worker build, which keeps
    // Node-specific wiring out of production code.
    if (!options.workerSrc) {
      const workerUrl = await import('pdfjs-dist/build/pdf.worker.mjs?url');
      options.workerSrc = workerUrl.default;
    }
    workerConfigured = true;
  }

  return pdfjs;
}

export async function extractTextFromPdf(fileBytes: Uint8Array): Promise<ExtractionResult> {
  const pdfjs = await loadPdfjs();

  // The loading task owns teardown; the document proxy has no destroy() in v6.
  //
  // The copy is REQUIRED: pdf.js takes ownership of the buffer and detaches it,
  // so passing the caller's array would leave them holding a zero-length view.
  // Without this, a user retrying a failed extraction gets an empty document.
  const loadingTask = pdfjs.getDocument({
    data: new Uint8Array(fileBytes),
    // No network access under any circumstances — this is the privacy guarantee,
    // enforced at the parser rather than trusting the parser's defaults.
    // (pdf.js v6 dropped isEvalSupported; it no longer uses eval at all.)
    disableFontFace: true,
    useSystemFonts: false,
  });
  const doc = await loadingTask.promise;

  try {
    const pages: string[] = [];

    for (let pageNumber = 1; pageNumber <= doc.numPages; pageNumber += 1) {
      const page = await doc.getPage(pageNumber);
      const content = await page.getTextContent();

      // Reinsert the whitespace pdf.js omits between adjacent text runs.
      //
      // pdf.js returns positioned runs with no separator, so a naive join fuses
      // words across run boundaries — "and" + "metadata" becomes "andmetadata",
      // which is unrecoverable. PyMuPDF breaks on layout instead.
      //
      // Guiding principle: ERR TOWARD INSERTING whitespace. cleanText() collapses
      // runs of spaces and newlines, so an extra separator costs nothing, while a
      // missing one destroys a word boundary permanently.
      let pageText = '';
      let previousX: number | null = null;
      let previousY: number | null = null;
      let previousWidth = 0;
      let justBrokeLine = false;

      for (const item of content.items) {
        if (!('str' in item)) continue;

        const x = item.transform[4] as number;
        const y = item.transform[5] as number;
        // Approximate font size from the transform's vertical scale, so the
        // thresholds below adapt to text size instead of assuming one.
        const fontSize = Math.hypot(item.transform[2] as number, item.transform[3] as number) || 10;

        if (!justBrokeLine && previousY !== null && previousX !== null) {
          if (Math.abs(y - previousY) > fontSize * LINE_BREAK_RATIO) {
            // New baseline: a line break.
            pageText += '\n';
          } else if (x - (previousX + previousWidth) > fontSize * WORD_GAP_RATIO) {
            // Same line, but a visible horizontal gap: a word break.
            pageText += ' ';
          }
        }

        pageText += item.str;

        justBrokeLine = item.hasEOL === true;
        if (justBrokeLine) pageText += '\n';

        previousX = x;
        previousY = y;
        previousWidth = item.width ?? 0;
      }

      pages.push(pageText);
      page.cleanup();
    }

    return {
      text: pages.join('\n\n').trim(),
      page_count: doc.numPages,
    };
  } finally {
    await loadingTask.destroy();
  }
}
