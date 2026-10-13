import type { Chunk } from '../../src/core/types';

const STOP = new Set(
  ('the a an and or of to in on for is are was were what how why who when which does did do with by as at from that this it be ' +
    'can could would should will you your me my u please tell give provide explain show describe its there their they them any also into than then has have had been not all more some about')
    .split(' ')
);

/** Questions made only of these words ask about the whole document (same idea as the desktop retriever). */
const OVERVIEW = new Set(
  'summary summarize summarise summarization overview document doc file pdf paper article content contents main point points idea ideas topic topics gist key takeaway takeaways whole entire'.split(' ')
);

/** Section questions: find the heading in the text and send that part of the document. */
const SECTIONS: { name: string; pattern: string }[] = [
  { name: 'Abstract', pattern: 'abstract' },
  { name: 'Introduction', pattern: 'introduction' },
  { name: 'Background', pattern: 'background|related work|literature review' },
  { name: 'Methods', pattern: 'methods?|methodology|approach|data and methods|research design|study design|empirical strategy|procedures?' },  
  { name: 'Discussion', pattern: 'discussion' },
  { name: 'Limitations', pattern: 'limitations?' },
  { name: 'Conclusion', pattern: 'conclusions?|concluding remarks' },
];

export const SYSTEM_PROMPT =
  'You are the PPLLM Assistant. Answer the question using only the document passages provided. ' +
  'Write in complete sentences, usually 2 to 5. When the question asks for a summary or for several items, use a short list. ' +
  'Explain in your own words; do not copy citation markers, page headers or broken fragments. ' +
  'If the passages only partly answer the question, answer the part they support and say what is missing. ' +
  'Only if the passages contain nothing related to the question, reply exactly: Not found in the document.';

export const TOP_K = 5;

export type Mode = 'keyword' | 'overview' | 'section';

/** Lowercase words, minus filler words; a trailing plural "s" is dropped so "methods" matches "method". */
export function tokenize(text: string): string[] {
  return (text.toLowerCase().match(/[a-z0-9$%]+/g) ?? [])
    .filter((w) => w.length > 1 && !STOP.has(w))
    .map((w) => (w.length > 4 && w.endsWith('s') && !w.endsWith('ss') ? w.slice(0, -1) : w));
}

/** Chunks spread evenly from the start to the end of the document, for summary questions. */
function spreadAcross(chunks: Chunk[], k: number): Chunk[] {
  if (chunks.length <= k) return chunks;
  const picks = new Set<number>();
  for (let i = 0; i < k; i++) picks.add(Math.round((i * (chunks.length - 1)) / (k - 1)));
  return chunks.filter((_, i) => picks.has(i));
}

/** Index of the chunk where the reference list starts, or chunks.length if there is none. */
function referencesStart(chunks: Chunk[]): number {
  const i = chunks.findIndex((c) => /(^|\n)[ \t]*(references|bibliography|works cited)[ \t]*(\n|$)/i.test(c.text));
  return i > 0 ? i : chunks.length;
}

/** A section heading on its own short line, plus the two chunks after it. Never looks in the reference list. */
function findSection(question: string, chunks: Chunk[]): { name: string; chunks: Chunk[] } | null {
  const q = question.toLowerCase();
  const body = chunks.slice(0, referencesStart(chunks));
  for (const s of SECTIONS) {
    if (!new RegExp(`\\b(${s.pattern})\\b`).test(q)) continue;
    const heading = new RegExp(`(^|\\n)[ \\t]*([0-9ivx]+(\\.[0-9]+)*\\.?[ \\t]+)?(${s.pattern})\\b[^\\n]{0,30}(\\n|$)`, 'i');
    const start = body.findIndex((c) => heading.test(c.text));
    if (start >= 0) return { name: s.name, chunks: body.slice(start, start + 3) };
  }
  return null;
}


/**
 * Score chunks by shared question words, weighting rare words higher (IDF).
 * A word found in every chunk ("ai") counts for little; a word found in one
 * chunk ("moderna") counts for a lot.
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
      return { chunk, score };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, TOP_K)
    .map((s) => s.chunk);
}

/** Pick the passages to send: whole-document overview, a named section, or keyword search. */
export function retrieve(question: string, chunks: Chunk[]): { mode: Mode; note: string; chunks: Chunk[] } {
  const q = question.toLowerCase();
  const wantsRefs = /\b(references?|citations?|cited|bibliography)\b/.test(q);
  const body = wantsRefs ? chunks : chunks.slice(0, referencesStart(chunks));
  const words = (q.match(/[a-z0-9$%]+/g) ?? []).filter((w) => w.length > 1 && !STOP.has(w));

  if (words.length > 0 && words.every((w) => OVERVIEW.has(w))) {
    return {
      mode: 'overview',
      note: 'These passages are spread from the start to the end of the document. Use them to describe what the whole document is about.',
      chunks: spreadAcross(body, TOP_K),
    };
  }

  const section = findSection(question, chunks);
  if (section) {
    return {
      mode: 'section',
      note: `These passages are the ${section.name} section of the document. Summarize what it says.`,
      chunks: section.chunks,
    };
  }

  const found = keywordSearch(question, body);
  if (found.length) return { mode: 'keyword', note: '', chunks: found };

  // A section was named but the document has no heading with that name: describe the document instead.
  const asked = SECTIONS.find((s) => new RegExp(`\\b(${s.pattern})\\b`).test(q));
  if (asked) {
    return {
      mode: 'overview',
      note: `This document has no section titled ${asked.name}. Mention that in one short sentence, then answer the question from these passages anyway, which are spread across the document. For methods, describe how the work was done: the research design or approach, the data, sources or participants, and how the results were measured or analyzed. Only describe the parts these passages actually mention, and skip the rest.`,
      chunks: spreadAcross(body, TOP_K),
    };
  }
  return { mode: 'keyword', note: '', chunks: [] };
}
