# Week 22 Transfer Notes: Browser-Based PPLLM Studio

## Purpose

Nick requested a lightweight browser-based PPLLM Studio on theLLMStore.com so NSF and IU grant managers can interact with the product concept before a funded backend exists.

The current implementation is intentionally static and front-end only. It is designed to communicate the PPLLM workflow, not to process real user files.

## Files Changed

- `website/ppllm-browser.html`
  - New browser proof-of-concept page.
  - Simulates ingest, processing, Assistant answers, and source preview.
  - Contains inline JavaScript for the demo state.
- `website/styles.css`
  - Adds browser-demo styles.
  - Keeps the page dependency-free and compatible with static Render hosting.
- `website/index.html`
  - Adds the browser prototype to the resource list.
- `website/ppllm-studio.html`
  - Adds navigation and callout links to the browser prototype.

## What Works Now

- Reviewers can launch a browser-based PPLLM Studio prototype.
- The demo shows a sample document.
- The demo simulates:
  - local file selection
  - extraction
  - cleaning
  - chunking
  - optional encryption
  - Assistant responses
  - source citation inspection
- No server, model, API, authentication, or database is required.

## What Is Simulated

- No actual file upload occurs.
- No file bytes are read by JavaScript.
- No PDF extraction occurs.
- No chunks are generated from real text.
- No Ollama or hosted LLM is called.
- Assistant answers and source chunks are hardcoded in `website/ppllm-browser.html`.

## Future Backend Path

When funding supports a real hosted version, replace the static JavaScript state with API calls:

1. Upload or browser-local file selection flow.
2. Server-side extraction and cleaning.
3. Chunk generation and artifact manifest storage.
4. Optional artifact encryption.
5. Retrieval over generated chunks.
6. Model connector for a local, hosted, or API-backed Assistant.
7. Source preview endpoint that returns the cited chunk text and metadata.

## Deployment Notes

The site is currently structured for Render static hosting:

- Render static publish path: `website`
- Current live site: `https://thellmstore.com`
- New browser page path after deploy: `https://thellmstore.com/ppllm-browser.html`

Before deployment, verify locally:

```bash
cd website
python3 -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000/ppllm-browser.html
```

## Recommended Next Developer Task

If continuing without backend funding, improve copy, screenshots, and grant-facing polish only.

If backend funding arrives, start by separating the inline JavaScript in `ppllm-browser.html` into a small app module and define the real API contract before implementing upload or model calls.
