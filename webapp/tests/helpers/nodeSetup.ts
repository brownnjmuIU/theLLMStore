// pdf.js in Node: point it at the legacy worker build so extraction runs on the main thread.
import { createRequire } from 'node:module';
import * as pdfjs from 'pdfjs-dist';

const require = createRequire(import.meta.url);
(pdfjs.GlobalWorkerOptions as { workerSrc: string }).workerSrc = require.resolve(
  'pdfjs-dist/legacy/build/pdf.worker.mjs'
);
