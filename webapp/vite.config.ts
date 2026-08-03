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
    // Parsers (pdf.js, mammoth, tesseract) are dynamically imported so they
    // never land in the initial bundle. Budget: < 250 KB gzipped.
    rollupOptions: {
      output: {
        manualChunks: undefined,
        // STABLE names for the entry point. website/ppllm-browser.html mounts the
        // app inline and has to reference these files by name, so a content hash
        // would break that page on every rebuild. Lazy chunks keep their hashes.
        // Cache-busting uses ?v= on the reference, matching the ?v=11 convention
        // already used for styles.css elsewhere on the site.
        entryFileNames: 'assets/ppllm-app.js',
        assetFileNames: (info) =>
          info.names?.[0]?.endsWith('.css')
            ? 'assets/ppllm-app.css'
            : 'assets/[name]-[hash][extname]',
      },
    },
  },
  worker: {
    format: 'es',
  },
});
