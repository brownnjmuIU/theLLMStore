import type { Chunk } from '../core/types';

/**
 * Retrieval for the Assistant: picks which passages go to the model.
 * Pure functions, no browser APIs, so tests/stress/stress.test.ts can run them in Node.
 *
 * Order of strategies:
 *   1. Small document: send the whole thing (nothing can be missed).
 *   2. Overview question ("summarize", "what is this paper about"): passages spread across the document.
 *   3. Section question ("methods", "results", "limitations"): that section, found by its heading.
 *   4. Keyword search, rare words weighted higher.
 *   5. Nothing matched: passages spread across the document, and the model decides.
 *      (Before Week 3 this step returned "Not found" without asking the model at all,
 *      which was the most common reason the Assistant "gave no answer".)
 */

const STOP = new Set(
  ('the a an and or of to in on for is are was were what how why who when which does did do with by as at from that this it be ' +
    'can could would should will you your me my u please tell give provide explain show describe its there their they them any also into than then has have had been not all more some about ' +
    'say says said whats there here much many')
    .split(' ')
);

/** Questions made only of these words ask about the whole document. */
const OVERVIEW = new Set(
  ('summary summarize summarise summarization overview document doc file pdf paper article content contents main point points idea ideas ' +
    'topic topics gist key takeaway takeaways whole entire report study memo post blog story piece text slides deck presentation ' +
    'purpose tldr brief briefly short overall big picture thesis argument central')
    .split(' ')
);

/** Section questions: find the heading in the text and send that part of the document. */
const SECTIONS: { name: string; pattern: string }[] = [
  { name: 'Abstract', pattern: 'abstract' },
  { name: 'Introduction', pattern: 'introduction' },
  { name: 'Background', pattern: 'background|related work|literature review|prior work' },
  {
    name: 'Methods',
    pattern:
      'methods?|methodology|approach|data and methods|materials and methods|research design|study design|empirical strategy|procedures?|experimental setup',
  },
  { name: 'Results', pattern: 'results?|findings?|main results|key findings|main findings' },
  { name: 'Discussion', pattern: 'discussion' },
  { name: 'Limitations', pattern: 'limitations?' },
  { name: 'Conclusion', pattern: 'conclusions?|concluding remarks' },
];

export const SYSTEM_PROMPT =
  'You answer questions about a document using only the document passages provided. ' +
  'The passages are the user\'s document; anything they describe (people, tools, assistants, studies) belongs to that document, not to you. ' +
  'Write in complete sentences, usually 2 to 5. When the question asks for a summary or for several items, use a short list. ' +
  'Explain in your own words; do not copy citation markers, page headers or broken fragments. ' +
  'Answer in the same language as the question. ' +
  'If the passages only partly answer the question, answer the part they support and say what is missing. ' +
  'If the message contains several questions, answer each one in turn. ' +
  'Only if the passages contain nothing related to the question, reply exactly: Not found in the document.';

export const TOP_K = 5;
/** Documents up to this many characters are sent whole: about 1,500 tokens, well inside the model's 4,096. */
const SMALL_DOC_CHARS = 6000;

export type Mode = 'whole' | 'overview' | 'section' | 'keyword' | 'fallback';

/** Fix text so the model and the keyword matcher see plain characters: ligatures, odd spaces, invisible marks. */
export function normalizeText(text: string): string {
  return text
    .normalize('NFKC') // "ﬁ" -> "fi", full-width digits -> digits
    .replace(/[­​-‏⁠﻿]/g, '') // soft hyphen, zero-width characters
    .replace(/[-�]/g, ' ') // private-use glyphs and "unknown character" boxes from bad PDF fonts
    .replace(/[ \t]{2,}/g, ' ');
}

/** Crude stemming so "findings", "finding" and "find" all match, and "methods" matches "method". */
function stem(w: string): string {
  if (w.length > 5 && w.endsWith('ings')) return w.slice(0, -4);
  if (w.length > 4 && w.endsWith('ing')) return w.slice(0, -3);
  if (w.length > 4 && w.endsWith('ies')) return w.slice(0, -3) + 'y';
  if (w.length > 4 && w.endsWith('ed')) return w.slice(0, -2);
  if (w.length > 4 && w.endsWith('s') && !w.endsWith('ss')) return w.slice(0, -1);
  return w;
}

/** Lowercase words (any alphabet), minus filler words, stemmed. */
export function tokenize(text: string): string[] {
  return (normalizeText(text).toLowerCase().match(/[\p{L}\p{N}$%]+/gu) ?? [])
    .filter((w) => w.length > 1 && !STOP.has(w))
    .map(stem);
}

/** Chunks spread evenly from the start to the end of the document. Always includes the first chunk (title, authors). */
function spreadAcross(chunks: Chunk[], k: number): Chunk[] {
  if (chunks.length <= k) return chunks;
  const picks = new Set<number>();
  for (let i = 0; i < k; i++) picks.add(Math.round((i * (chunks.length - 1)) / (k - 1)));
  return chunks.filter((_, i) => picks.has(i));
}

const REFERENCES_HEADING = /(^|\n)[ \t]*(references|bibliography|works cited|literature cited)[ \t]*:?[ \t]*(\n|$)/i;

/**
 * The document without its reference list. The chunk where the list starts is CUT at the
 * heading rather than dropped, because that chunk usually also holds the end of the
 * Conclusion. Uses the LAST "References" heading, so a table of contents can't trigger it.
 */
export function withoutReferences(chunks: Chunk[]): Chunk[] {
  for (let i = chunks.length - 1; i > 0; i--) {
    const chunk = chunks[i];
    if (!chunk) continue;
    const m = REFERENCES_HEADING.exec(chunk.text);
    if (m) {
      const kept = chunk.text.slice(0, m.index).trim();
      const before = chunks.slice(0, i);
      return kept ? [...before, { ...chunk, text: kept }] : before;
    }
  }
  return chunks;
}

/**
 * A line that IS a heading: optional numbering ("3.", "III.", "3.1"), the section word, up to two
 * "and X" words ("Results and Discussion"), optional colon, then end of line. Earlier versions also
 * accepted ordinary text lines that merely started with the word, which in two-column PDFs (short
 * lines) matched sentences like "approach described in the following".
 */
function headingRegex(pattern: string): RegExp {
  return new RegExp(
    `(^|\\n)[ \\t]*((\\d+|[ivxlc]+)(\\.\\d+)*\\.?[ \\t]+)?(${pattern})([ \\t]+(and|&)[ \\t]+[\\p{L}]+){0,2}[ \\t]*[:.]?[ \\t]*(\\n|$)`,
    'iu'
  );
}

/** "Abstract: We study…" or "ABSTRACT—We study…" — a capitalised heading run into the paragraph. */
function inlineHeadingRegex(pattern: string): RegExp {
  const capitalised = pattern
    .split('|')
    .map((p) => `${p[0]?.toUpperCase()}${p.slice(1)}|${p.toUpperCase()}`)
    .join('|');
  return new RegExp(`(^|\\n)[ \\t]*(${capitalised})[ \\t]*[:.\\u2014\\u2013-][ \\t]*\\p{L}`, 'u');
}

function findSection(question: string, body: Chunk[]): { name: string; chunks: Chunk[] } | null {
  const q = question.toLowerCase();
  for (const s of SECTIONS) {
    if (!new RegExp(`\\b(${s.pattern})\\b`).test(q)) continue;
    const own = headingRegex(s.pattern);
    const inline = inlineHeadingRegex(s.pattern);
    let start = body.findIndex((c) => own.test(c.text));
    if (start < 0) start = body.findIndex((c) => inline.test(c.text));
    if (start >= 0) return { name: s.name, chunks: body.slice(start, start + 3) };
  }
  return null;
}

/**
 * Score chunks by shared question words, weighting rare words higher (IDF).
 * A word found in every chunk ("ai") counts for little; a word found in one chunk ("moderna") counts for a lot.
 */
function keywordSearch(question: string, chunks: Chunk[]): Chunk[] {
  const q = new Set(tokenize(question));
  const chunkWords = chunks.map((chunk) => new Set(tokenize(chunk.text)));
  const n = chunks.length;

  const idf = new Map<string, number>();
  q.forEach((w) => {
    const df = chunkWords.filter((words) => words.has(w)).length;
    idf.set(w, df === 0 ? 0 : Math.log(1 + n / df));
  });

  return chunks
    .map((chunk, i) => {
      let score = 0;
      q.forEach((w) => {
        if (chunkWords[i]?.has(w)) score += idf.get(w) ?? 0;
      });
      return { chunk, score, i };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, TOP_K)
    .sort((a, b) => a.i - b.i) // keep document order so the model reads passages as written
    .map((s) => s.chunk);
}

export type Retrieved = { mode: Mode; note: string; chunks: Chunk[] };

/** Pick the passages to send to the model. */
function retrieveOne(question: string, allChunks: Chunk[]): Retrieved {
  const chunks = allChunks.map((c) => ({ ...c, text: normalizeText(c.text) }));
  const q = normalizeText(question).toLowerCase();
  const wantsRefs = /\b(references?|citations?|cited|bibliography|sources)\b/.test(q);
  const body = wantsRefs ? chunks : withoutReferences(chunks);
  if (!body.length) return { mode: 'keyword', note: '', chunks: [] };

  const totalChars = body.reduce((sum, c) => sum + c.text.length, 0);
  if (totalChars <= SMALL_DOC_CHARS) {
    return { mode: 'whole', note: 'These passages are the entire document.', chunks: body };
  }

  const words = (q.match(/[\p{L}\p{N}$%]+/gu) ?? []).filter((w) => w.length > 1 && !STOP.has(w));
  if (words.length > 0 && words.every((w) => OVERVIEW.has(w))) {
    return {
      mode: 'overview',
      note: 'These passages are spread from the start to the end of the document. Use them to describe what the whole document is about.',
      chunks: spreadAcross(body, TOP_K),
    };
  }

  const section = findSection(question, body);
  if (section) {
    return {
      mode: 'section',
      note: `These passages are the ${section.name} section of the document. Summarize what it says.`,
      chunks: section.chunks,
    };
  }

  const found = keywordSearch(question, body);
  if (found.length) return { mode: 'keyword', note: '', chunks: found };

  // A section was named but the document has no heading with that name.
  const asked = SECTIONS.find((s) => new RegExp(`\\b(${s.pattern})\\b`).test(q));
  if (asked) {
    return {
      mode: 'overview',
      note: `This document has no section titled ${asked.name}. Mention that in one short sentence, then answer the question from these passages anyway, which are spread across the document. Only describe what these passages actually say.`,
      chunks: spreadAcross(body, TOP_K),
    };
  }

  // No word of the question appears in the document ("Who wrote it?", synonyms, another language).
  return {
    mode: 'fallback',
    note: 'No passage shares words with the question, so these passages are spread across the document. Answer only if they contain the answer.',
    chunks: spreadAcross(body, TOP_K),
  };
}

/* ------------------------------------------------------------------ */
/* Quality checks: tell the user when the PROBLEM is the file or the model */
/* ------------------------------------------------------------------ */

export type Quality = { level: 'ok' | 'empty' | 'garbled' | 'thin'; message: string };

/**
 * Is the extracted text readable? Catches scans (no text layer) and PDFs whose fonts
 * have no proper character map, which pdf.js turns into strings like "Ã¾ÄŸ" or boxes.
 */
export function documentQuality(chunks: Chunk[]): Quality {
  const text = normalizeText(chunks.map((c) => c.text).join('\n'));
  const letters = (text.match(/\p{L}/gu) ?? []).length;
  if (letters < 40) {
    return {
      level: 'empty',
      message:
        'This file has almost no readable text. It is probably a scan or a picture of a page. Take a screenshot of the page and upload it as an image (PNG or JPG) so the app can read it with OCR.',
    };
  }
  const tokens = text.split(/\s+/).filter((t) => /\p{L}/u.test(t) && !/\d/.test(t)); // numbers and codes like Q4, $4.8M are not words
  const wordLike = tokens.filter((t) => /^[\p{L}][\p{L}'’-]*[\p{L}]?[.,;:!?)"”]*$/u.test(t.replace(/^[("“]/, '')) && t.length < 25);
  const odd = (text.match(/[\u0080-ÿ]{2,}|[^\p{L}\p{N}\p{P}\p{S}\p{Z}\n\t]/gu) ?? []).length;
  if (tokens.length > 20 && (wordLike.length / tokens.length < 0.6 || odd / tokens.length > 0.15)) {
    return {
      level: 'garbled',
      message:
        'The text in this PDF did not extract cleanly (the PDF uses fonts the reader cannot decode), so answers will be unreliable. Try re-saving it with "Print to PDF", or upload a Word version of the document.',
    };
  }
  if (letters < 400) {
    return { level: 'thin', message: 'This document is very short, so the Assistant can only answer questions about these few lines.' };
  }
  return { level: 'ok', message: '' };
}

/**
 * Does a model answer look like corrupted output rather than language? This is the signature of a
 * WebGPU numeric-precision failure (16-bit math on some Windows GPUs and drivers), as in the
 * "According Negot.enginJev J juev plays the.forms of Doom" answer: words glued with periods,
 * random scripts mixed into English, and fragments.
 */
export function looksGarbled(answer: string, documentText = ''): boolean {
  const tokens = answer.split(/\s+/).filter(Boolean);
  if (tokens.length < 8) return false;
  const docHasScript = (re: RegExp) => re.test(documentText);
  const foreign = [/\p{Script=Han}/u, /\p{Script=Arabic}/u, /\p{Script=Cyrillic}/u, /\p{Script=Thai}/u, /\p{Script=Hangul}/u].filter(
    (re) => re.test(answer) && !docHasScript(re)
  ).length;
  const glued = tokens.filter((t) => /\p{Ll}\.\p{L}/u.test(t) && !/^(e\.g|i\.e|u\.s|a\.m|p\.m|et\.al)/i.test(t) && !/\.(com|org|net|edu|ai|io|dev|gov|pdf)\b/i.test(t)).length;
  const singleCaps = tokens.filter((t) => /^[A-Z]\.?$/.test(t) && t !== 'A' && t !== 'I').length;
  const score = foreign * 4 + glued + singleCaps * 0.5;
  return score / tokens.length > 0.08 || foreign >= 2;
}

/**
 * Pick the passages to send to the model. A message with several questions
 * ("What are the limitations? Who wrote it?") is split, each part retrieves its own
 * passages, and the results are merged in document order (at most 7 passages).
 */
export function retrieve(question: string, allChunks: Chunk[]): Retrieved {
  const parts = question
    .split('?')
    .map((p) => p.trim())
    .filter((p) => (p.match(/[\p{L}\p{N}]+/gu) ?? []).length >= 2);
  if (parts.length < 2) return retrieveOne(question, allChunks);

  const results = parts.map((p) => retrieveOne(p + '?', allChunks));
  if (results.some((r) => r.mode === 'whole')) return results.find((r) => r.mode === 'whole')!;
  const seen = new Map<string, Chunk>();
  for (const r of results) for (const c of r.chunks) if (!seen.has(c.chunk_id)) seen.set(c.chunk_id, c);
  const order = new Map(allChunks.map((c, i) => [c.chunk_id, i]));
  const merged = [...seen.values()].sort((a, b) => (order.get(a.chunk_id) ?? 0) - (order.get(b.chunk_id) ?? 0)).slice(0, 7);
  return {
    mode: results[0]?.mode ?? 'keyword',
    note: `The message asks ${parts.length} questions. Answer each one separately. ` + results.map((r) => r.note).filter(Boolean).join(' '),
    chunks: merged,
  };
}
