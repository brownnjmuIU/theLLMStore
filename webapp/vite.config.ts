import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The app is served from https://thellmstore.com/studio/ and built INTO the
// existing published directory (website/), so render.yaml stays untouched and
// the live site is unaffected. See CLAUDE.md section 10.1.
export default defineConfig({
  base: '/studio/',
  plugins: [react()],
  server: {
    // Pinned to IPv4 on purpose. Vite 8 binds [::1] only by default, so anything
    // resolving "localhost" to 127.0.0.1 — including Playwright's webServer probe
    // — silently fails to connect.
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: '../website/studio',
    emptyOutDir: true,
    // Parsers (pdf.js, mammoth, tesseract) are dynamically imported in Phase 1
    // so they never land in the initial bundle. Budget: < 250 KB gzipped.
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
  worker: {
    format: 'es',
  },
});
