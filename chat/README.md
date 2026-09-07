# PPLLM Studio — Chat

A deliberately small chatbot. The browser talks to this Node server; this server
holds the API key and talks to an OpenAI-compatible LLM endpoint. The key never
reaches the browser, which is why this is a Render **Web Service** and not a
Static Site.

Self-contained: it does not import from `webapp/`, does not build into
`website/`, and does not touch the root `render.yaml`. The live site is
unaffected by anything in this folder.

## Architecture

```
browser (public/index.html)
   |  POST /api/chat  { messages: [...] }
   v
server.js            <- LLM_API_KEY lives here, in env, never in git
   |  OpenAI SDK, baseURL = LLM_BASE_URL
   v
Gemini (or DeepSeek, or a self-hosted vLLM — all env-var swaps)
```

The server is **stateless**. The browser owns the conversation and sends the
full history each turn, so there is no session store and concurrent users cannot
collide.

## Configuration

All three are required; the server exits at boot if any is missing, so a
misconfigured deploy fails visibly instead of erroring on first use.

| Variable       | Purpose                     |
| -------------- | --------------------------- |
| `LLM_BASE_URL` | OpenAI-compatible base URL  |
| `LLM_API_KEY`  | Provider key. Never commit. |
| `LLM_MODEL`    | Model string                |
| `PORT`         | Set by Render automatically |

Switching providers is a change to these values plus a redeploy — no code edit.

## Local development

```bash
cd chat
npm install
cp .env.example .env    # then paste your key into .env
npm run dev             # http://localhost:3000
```

`.env` is gitignored. `.env.example` is the committed template and holds no real
values.

## Deploying to Render

Create the service **in the dashboard**, not by editing the root `render.yaml` —
that file describes the existing live static site, and leaving it untouched
keeps this work isolated from it.

1. New → Web Service, pointed at this repo.
2. **Branch:** `feature/ai-chat` (a per-service setting, so the live site's
   service is unaffected).
3. **Root Directory:** `chat`
4. **Build Command:** `npm install`
5. **Start Command:** `npm start`
6. Add `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` under Environment.

`/healthz` returns `{ ok, model }`, which is the quickest way to confirm which
model a deploy is actually running.

### Known constraints

- **Free-tier services sleep after ~15 minutes idle**, and the cold start takes
  30–60s. Load the URL a few minutes before demoing so the first request is not
  mistaken for a hang.
- **The endpoint is public and unauthenticated.** Anyone with the URL can spend
  the quota. Message-count and length caps in `server.js` are a floor, not
  security.

## Notes on Gemini's OpenAI compatibility layer

- It is beta and **silently drops parameters it does not support**, so requests
  here stay plain chat completions. An unsupported option fails quietly.
- An invalid API key comes back as **HTTP 400 with an empty body**, not the 401
  the OpenAI spec implies (verified against the live endpoint 2026-09-07).
  `describeUpstreamError()` treats an upstream 400 as a config problem, which is
  sound because request shape is validated before anything is sent upstream.
- Model strings verified against ai.google.dev on 2026-09-07: `gemini-3.8-flash`
  is current (released 09-02). `gemini-2.5-flash` is still available; it is
  _2.0_ Flash that was shut down.

## Out of scope

RAG, document upload, citations, auth, persistence, and any integration with the
`webapp/` pipeline. Shipping small and on time was the explicit goal.
