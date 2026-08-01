import type { ExtractionResult } from '../core/types';

/**
 * Port of extractors/pptx_extractor.py.
 *
 * No JavaScript equivalent of python-pptx exists, but a .pptx is just a ZIP of
 * XML. Slide text lives in ppt/slides/slideN.xml as <a:t> runs inside <a:p>
 * paragraphs — which is exactly what python-pptx reads underneath.
 *
 * Matching the Python output:
 *   - paragraph.text is the concatenation of every run in that paragraph
 *   - empty paragraphs are dropped
 *   - paragraphs within a slide join with "\n"
 *   - slides join with "\n\n---\n\n"
 *   - page_count is the slide count
 *
 * Shares python-pptx's limitation deliberately: only shapes with a text frame.
 * Charts, images, tables and speaker notes are not extracted by either.
 */

/**
 * Slides are ordered by the number in the filename.
 *
 * The strictly correct order comes from ppt/_rels/presentation.xml.rels, but
 * slideN.xml numbering matches presentation order in every deck produced by
 * PowerPoint, Keynote or Google Slides. The important part is NUMERIC sorting:
 * a lexicographic sort would place slide10 before slide2.
 */
function slideNumber(path: string): number {
  const match = /slide(\d+)\.xml$/.exec(path);
  return match?.[1] ? Number(match[1]) : Number.MAX_SAFE_INTEGER;
}

/** Decode the five XML predefined entities. Order matters: &amp; must come last. */
function decodeXmlEntities(text: string): string {
  return text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, code: string) => String.fromCodePoint(Number(code)))
    .replace(/&amp;/g, '&');
}

/** Extract one slide's text, preserving paragraph boundaries. */
function textFromSlideXml(xml: string): string[] {
  const paragraphs: string[] = [];

  // <a:p> … </a:p> is a paragraph; <a:t> … </a:t> are the runs inside it.
  for (const paragraphMatch of xml.matchAll(/<a:p\b[^>]*>([\s\S]*?)<\/a:p>/g)) {
    const body = paragraphMatch[1] ?? '';
    let text = '';
    for (const runMatch of body.matchAll(/<a:t\b[^>]*>([\s\S]*?)<\/a:t>/g)) {
      text += decodeXmlEntities(runMatch[1] ?? '');
    }
    const trimmed = text.trim();
    if (trimmed) paragraphs.push(trimmed);
  }

  return paragraphs;
}

export async function extractTextFromPptx(fileBytes: Uint8Array): Promise<ExtractionResult> {
  const { default: JSZip } = await import('jszip');
  const zip = await JSZip.loadAsync(fileBytes);

  const slidePaths = Object.keys(zip.files)
    .filter((path) => /^ppt\/slides\/slide\d+\.xml$/.test(path))
    .sort((a, b) => slideNumber(a) - slideNumber(b));

  const slides: string[] = [];
  for (const path of slidePaths) {
    const file = zip.file(path);
    if (!file) continue;

    const paragraphs = textFromSlideXml(await file.async('string'));
    // Python appends only slides that produced text, but still counts them all.
    if (paragraphs.length > 0) slides.push(paragraphs.join('\n'));
  }

  return {
    text: slides.join('\n\n---\n\n').trim(),
    page_count: slidePaths.length,
  };
}
