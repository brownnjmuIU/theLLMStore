/**
 * Lazy entry point for WebLLM. Assistant.tsx loads this with
 * `await import('./webllm')` only when the user clicks "Load AI model",
 * so the ~2 MB library is never part of the initial page load.
 * It is its own file so the build names the chunk webllm-*.js, which the
 * CI bundle budget treats as a lazy chunk (like pdf-*.js and docx-*.js).
 */
export { CreateMLCEngine } from '@mlc-ai/web-llm';