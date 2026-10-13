/**
 * PPLLM Assistant stress test.
 *
 * Runs every PDF in tests/stress/corpus through the SAME code the browser uses
 * (pdf.js extraction -> cleanText -> chunkText -> retrieve) and checks, for each
 * question with a known answer, whether the passages sent to the model contain it.
 * If the answer is not in the passages, no model can answer correctly, so this
 * isolates retrieval and extraction failures from model failures.
 *
 * Writes tests/stress/report.md and compares the old retrieval with the new one.
 */
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { extractTextFromPdf } from '../../src/extractors/pdf';
import { processDocument } from '../../src/core/pipeline';
import type { Chunk, RawArtifact } from '../../src/core/types';
import * as baseline from './retrieval_baseline';
import * as current from '../../src/ui/retrieval';

const DIR = join(__dirname, 'corpus');
const questions: Record<string, { q: string; expect: string[] }[]> = JSON.parse(
  readFileSync(join(DIR, 'questions.json'), 'utf8')
);

type Row = { file: string; q: string; old: string; now: string; oldHit: boolean; nowHit: boolean };

function hit(chunks: Chunk[], expectAny: string[]): boolean {
  const text = chunks.map((c) => c.text.toLowerCase()).join('\n');
  return expectAny.some((e) => text.includes(e.toLowerCase()));
}

describe('assistant stress corpus', () => {
  it('runs every document and question', async () => {
    const rows: Row[] = [];
    const docNotes: string[] = [];

    for (const file of readdirSync(DIR).filter((f) => f.endsWith('.pdf')).sort()) {
      let chunks: Chunk[] = [];
      let note = '';
      try {
        const bytes = new Uint8Array(readFileSync(join(DIR, file)));
        const extracted = await extractTextFromPdf(bytes);
        const raw = {
          doc_id: file,
          source_filename: file,
          file_type: 'pdf',
          text: extracted.text,
        } as unknown as RawArtifact;
        chunks = processDocument(raw).chunks;
        const text = extracted.text;
        const ligatures = (text.match(/[ﬀ-ﬆ]/g) ?? []).length;
        note = `${extracted.page_count} pages, ${text.length} chars, ${chunks.length} chunks` +
          (ligatures ? `, ${ligatures} ligature glyphs` : '');
        if ('documentQuality' in current) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const qual = (current as any).documentQuality(chunks);
          note += `, quality check: ${qual.level}${qual.message ? ' ("' + qual.message + '")' : ''}`;
        }
      } catch (error) {
        note = `EXTRACTION FAILED: ${error instanceof Error ? error.message : String(error)}`;
      }
      docNotes.push(`| ${file} | ${note} |`);

      for (const { q, expect: ex } of questions[file] ?? []) {
        const o = baseline.retrieve(q, chunks);
        const n = current.retrieve(q, chunks);
        rows.push({
          file,
          q,
          old: `${o.mode}/${o.chunks.length}`,
          now: `${n.mode}/${n.chunks.length}`,
          oldHit: hit(o.chunks, ex),
          nowHit: hit(n.chunks, ex),
        });
      }
    }

    const oldScore = rows.filter((r) => r.oldHit).length;
    const nowScore = rows.filter((r) => r.nowHit).length;
    const md = [
      '# PPLLM Assistant stress test',
      '',
      `Answer reached the model: **before ${oldScore}/${rows.length}**, **after ${nowScore}/${rows.length}**`,
      '',
      '## Documents',
      '| File | Extraction |',
      '|---|---|',
      ...docNotes,
      '',
      '## Questions',
      '| File | Question | Before (mode/passages) | Before | After | After |',
      '|---|---|---|---|---|---|',
      ...rows.map(
        (r) => `| ${r.file} | ${r.q} | ${r.old} | ${r.oldHit ? 'yes' : '**NO**'} | ${r.now} | ${r.nowHit ? 'yes' : '**NO**'} |`
      ),
    ].join('\n');
    writeFileSync(join(__dirname, 'report.md'), md);
    console.log(md);
    expect(rows.length).toBeGreaterThan(0);
  }, 120_000);
});

describe('garbled answer detector', () => {
  // The answer from Nick's screenshot (Edge on Windows, shipwithjev.pdf).
  const nick =
    'According Negot.enginJev J juev plays the.forms of Doom. adjoining the game. thái Jev J accountable for the. Trooper. ' +
    'Jrelated to the. trooper J Attached to J. associated with J. 條 Jev ستر Jev .aniums .alternative to the. Flashy .trooper. ' +
    'Theassociated with this. izzling 204,locker Thealinguchi, Jfade';
  const good = [
    'Jev plays Doom by sending a summary of each game frame to the model and asking three typed questions: which weapon to use, whether to strafe left or right, and how threatening the scene is. It answers in about 90 milliseconds.',
    'The authors ran a field experiment with 412 analysts (e.g. 206 treated and 206 controls) and estimated effects with OLS. See shipwithjev.dev for details.',
    'Not found in the document.',
    '- Treated analysts completed 23 percent more reports.\n- Errors fell from 6.1 to 4.4 percent.\n- Gains were largest for novices.',
  ];
  it('flags the screenshot answer', () => expect(current.looksGarbled(nick, 'Jev plays Doom')).toBe(true));
  it.each(good)('does not flag a normal answer: %s', (a) => expect(current.looksGarbled(a)).toBe(false));
});
