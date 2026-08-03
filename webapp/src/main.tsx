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

/**
 * When mounted inside an existing page (website/ppllm-browser.html), that page
 * already provides the site header, hero and footer — so the app must not render
 * its own, or the visitor sees two navigation bars.
 */
const embedded = container.hasAttribute('data-embedded');

createRoot(container).render(
  <StrictMode>
    <App embedded={embedded} />
  </StrictMode>
);
