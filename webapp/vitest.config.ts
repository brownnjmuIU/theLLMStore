import { defineConfig } from 'vitest/config';

// Tests run in Node, not a browser. This is deliberate and only possible because
// src/core/ imports nothing browser-specific — the rule stated in CLAUDE.md
// section 10.4. If a core module ever needs `window`, that rule has been broken.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    reporters: ['verbose'],
    setupFiles: ['./tests/helpers/nodeSetup.ts'],
    // pdf.js on real documents is slower than the default 5s allows.
    testTimeout: 30_000,
  },
  resolve: {
    alias: {
      // pdf.js's default build assumes a browser. The legacy build is the one
      // intended for Node. Aliased HERE rather than branching inside
      // src/extractors/pdf.ts, so production code stays free of test concerns.
      'pdfjs-dist': 'pdfjs-dist/legacy/build/pdf.mjs',
    },
  },
});
