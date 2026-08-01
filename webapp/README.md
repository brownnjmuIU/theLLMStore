# PPLLM Studio — browser port

Client-side rebuild of the LLM Bundler desktop app. Extract → clean → chunk →
store → optionally encrypt, running entirely in the browser. No server, no upload,
no install. See `CLAUDE.md` section 10 at the repo root for the full plan.

**Status: Phase 0 complete.** Scaffold and conformance harness exist; the pipeline
is not implemented. `src/core/*` are documented stubs that throw.

## Setup

```bash
cd webapp
npm install
```

## Commands

| Command | Purpose |
|---|---|
| `npm run dev` | Dev server at http://127.0.0.1:5173/studio/ |
| `npm run build` | Production build into `../website/studio/` |
| `npm run typecheck` | Typecheck `src/` (what CI runs) |
| `npm run typecheck:test` | Typecheck `src/` + `tests/` (local only) |
| `npm test` | Conformance + unit suite |
| `npm run test:e2e` | Playwright, all three engines (Phase 1+) |

## Conformance

The suite compares against golden files generated from the **working Python
pipeline**. Regenerate them from the repo root:

```bash
.venv/bin/python3 conformance/generate_fixtures.py
.venv/bin/python3 conformance/generate_fixtures.py --check   # detect drift
```

Two tiers, because exact end-to-end equality with Python is impossible — pdf.js and
PyMuPDF are different engines and will never produce identical text:

- **Tier 1 (exact):** cleaner, chunker, docId, crypto must match byte-for-byte.
- **Tier 2 (similarity):** extractors are held to thresholds — page count exact,
  ≥0.95 character overlap, key phrases present, never empty from a text-bearing file.

## Tests are not committed

`tests/`, `conformance/` and `evaluation/` are gitignored by project instruction.
CI therefore runs typecheck and build only — **conformance must be run locally.**
The suite exists only on the developer's machine; back it up.

## The rule that makes this work

`src/core/` must import nothing browser-specific — no `window`, no `fetch`, no
IndexedDB. That is what lets the pipeline be tested in Node and compared directly
against Python. I/O lives in `src/storage/`, `src/crypto/` and `src/workers/`.

## Unicode

Python strings are code points; JavaScript strings are UTF-16 units. Inside
`src/core/`, never use `.length` or `[i]` on user text — use the helpers in
`src/core/unicode.ts`. Fixtures 005 and 012 fail if this is ignored.
