import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
// Reuse the existing site stylesheet rather than inventing a second design
// system. It is fully self-contained — no url(), no @import, no web fonts — so
// bundling it is safe and keeps this app visually continuous with the live site.
import '../../website/styles.css';
import { App } from './ui/App';

const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element #root not found');
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>
);
