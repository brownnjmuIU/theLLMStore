#!/usr/bin/env node
/**
 * Vendors the Tesseract assets into public/tesseract/ so OCR runs entirely
 * same-origin.
 *
 * WHY THIS EXISTS: tesseract.js fetches its worker, WASM core and language data
 * from cdn.jsdelivr.net by default. That would send requests off-origin during
 * processing, breaking the local-only guarantee this project rests on — and the
 * Playwright network test would (correctly) fail the build.
 *
 * LANGUAGE DATA: taken from the LOCAL Tesseract install when present, so the
 * browser runs the exact same model as the Python desktop app. Falls back to the
 * tesseract.js copy otherwise.
 *
 * public/tesseract/ is gitignored — regenerate with `npm run vendor:tesseract`.
 * Only the build output in website/studio/ is committed.
 */

import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(here, '../public/tesseract');

/** LSTM-only SIMD build: the smallest core that matches Tesseract 5's engine. */
const CORE_VARIANT = 'tesseract-core-simd-lstm.wasm.js';

function mb(path) {
  return (statSync(path).size / 1048576).toFixed(1);
}

function findLocalTessdata() {
  // The traineddata the installed Tesseract actually uses — best parity.
  try {
    const out = execSync('tesseract --list-langs 2>&1', { encoding: 'utf-8' });
    const match = /in "([^"]+)"/.exec(out);
    if (match?.[1]) {
      const candidate = join(match[1], 'eng.traineddata');
      if (existsSync(candidate)) return candidate;
    }
  } catch {
    /* Tesseract not installed locally — fall through. */
  }

  // Fallback: anything tesseract.js shipped.
  try {
    const dir = dirname(require.resolve('tesseract.js/package.json'));
    for (const name of readdirSync(dir)) {
      if (name === 'eng.traineddata') return join(dir, name);
    }
  } catch {
    /* ignore */
  }
  return null;
}

mkdirSync(OUT, { recursive: true });

const copied = [];

// 1. Worker script.
const workerSrc = join(dirname(require.resolve('tesseract.js/package.json')), 'dist/worker.min.js');
copyFileSync(workerSrc, join(OUT, 'worker.min.js'));
copied.push(['worker.min.js', join(OUT, 'worker.min.js')]);

// 2. WASM core. The loader .js may reference a sibling .wasm, so copy both.
const coreDir = dirname(require.resolve('tesseract.js-core/package.json'));
for (const name of [CORE_VARIANT, CORE_VARIANT.replace(/\.js$/, '')]) {
  const src = join(coreDir, name);
  if (existsSync(src)) {
    copyFileSync(src, join(OUT, name));
    copied.push([name, join(OUT, name)]);
  }
}

// 3. Language data.
const tessdata = findLocalTessdata();
if (tessdata) {
  copyFileSync(tessdata, join(OUT, 'eng.traineddata'));
  copied.push([`eng.traineddata  (from ${tessdata})`, join(OUT, 'eng.traineddata')]);
} else {
  console.error(
    '\n  WARNING: no eng.traineddata found.\n' +
      '  Install Tesseract (brew install tesseract) and re-run, or OCR will not work.\n'
  );
}

let total = 0;
console.log(`Vendored Tesseract assets -> ${OUT}\n`);
for (const [label, path] of copied) {
  const size = Number(mb(path));
  total += size;
  console.log(`  ${label.padEnd(56)} ${size.toFixed(1)} MB`);
}
console.log(`\n  TOTAL ${total.toFixed(1)} MB — served same-origin, never from a CDN.`);
