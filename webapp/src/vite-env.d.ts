/// <reference types="vite/client" />

/**
 * Vite's `?url` suffix imports resolve to a string URL at build time. The app
 * tsconfig sets `types: []` to keep Node types out of browser code, so this
 * reference is what makes those imports type-check.
 */
declare module '*?url' {
  const url: string;
  export default url;
}
