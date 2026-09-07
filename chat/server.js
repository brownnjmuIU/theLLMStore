import "dotenv/config";
import express from "express";
import OpenAI from "openai";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// -----------------------------------------------------------------------------
// Configuration
//
// Provider, model and key are ALL env vars so that swapping Gemini for DeepSeek
// or an IU-hosted vLLM is an environment change plus a redeploy, never a code
// edit. That is the whole reason this talks to an OpenAI-COMPATIBLE endpoint
// rather than Google's native SDK.
// -----------------------------------------------------------------------------
const BASE_URL = process.env.LLM_BASE_URL;
const API_KEY = process.env.LLM_API_KEY;
const MODEL = process.env.LLM_MODEL;

// Fail at boot, not on the first user request. A missing key on Render should
// show up as a failed deploy you notice, not a 500 the first time Nick types.
const missing = Object.entries({
  LLM_BASE_URL: BASE_URL,
  LLM_API_KEY: API_KEY,
  LLM_MODEL: MODEL,
})
  .filter(([, v]) => !v)
  .map(([k]) => k);

if (missing.length > 0) {
  console.error(
    `Missing required environment variable(s): ${missing.join(", ")}`,
  );
  console.error(
    "Copy .env.example to .env for local dev, or set them in the Render dashboard.",
  );
  process.exit(1);
}

const client = new OpenAI({ apiKey: API_KEY, baseURL: BASE_URL });

const SYSTEM_PROMPT =
  "You are a helpful assistant for PPLLM Studio. Be concise and direct.";

// Guard rails. This endpoint is public and unauthenticated, so anyone with the
// URL can spend the free-tier quota. These caps are a floor, not real security.
const MAX_MESSAGES = 40;
const MAX_CHARS_PER_MESSAGE = 8000;

const app = express();
app.use(express.json({ limit: "100kb" }));

/**
 * Reject anything that is not a well-formed chat history before it costs a
 * request upstream. Returns an error string, or null when the input is valid.
 */
function validateMessages(messages) {
  if (!Array.isArray(messages) || messages.length === 0) {
    return 'Request body must include a non-empty "messages" array.';
  }
  if (messages.length > MAX_MESSAGES) {
    return `Conversation too long (max ${MAX_MESSAGES} messages). Start a new chat.`;
  }
  for (const m of messages) {
    if (!m || (m.role !== "user" && m.role !== "assistant")) {
      return 'Each message needs a role of "user" or "assistant".';
    }
    if (typeof m.content !== "string" || m.content.trim() === "") {
      return "Each message needs non-empty string content.";
    }
    if (m.content.length > MAX_CHARS_PER_MESSAGE) {
      return `Message too long (max ${MAX_CHARS_PER_MESSAGE} characters).`;
    }
  }
  return null;
}

/**
 * Turn an upstream failure into something a human can act on. The browser shows
 * this text verbatim, so it must never leak the key, the base URL, or a stack
 * trace. Readable rate-limit errors are an explicit requirement of the MVP.
 */
function describeUpstreamError(err) {
  const status = err?.status ?? err?.response?.status;

  if (status === 429) {
    return {
      status: 429,
      error:
        "Rate limit reached on the free tier. Wait a minute and try again — the quota resets on a rolling window.",
    };
  }
  // Gemini's OpenAI compat layer answers an invalid key with 400 and NO body,
  // not the 401 the OpenAI spec implies. Verified against the live endpoint on
  // 2026-09-07. Because validateMessages() already rejected malformed input
  // before we got here, an upstream 400 means our own configuration is wrong.
  if (status === 400 || status === 401 || status === 403) {
    return {
      status: 502,
      error:
        "The model provider rejected this request. That usually means the server's API key or model name is misconfigured — check the deploy logs.",
    };
  }
  if (status === 404) {
    return {
      status: 502,
      error: `The model "${MODEL}" was not found at this provider. Check the LLM_MODEL value.`,
    };
  }
  if (status >= 500) {
    return {
      status: 502,
      error: "The model provider is having problems. Try again shortly.",
    };
  }
  return { status: 500, error: "Something went wrong talking to the model." };
}

app.post("/api/chat", async (req, res) => {
  const { messages } = req.body ?? {};

  const invalid = validateMessages(messages);
  if (invalid) return res.status(400).json({ error: invalid });

  try {
    // Plain chat completions on purpose. Gemini's OpenAI compat layer is beta
    // and silently DROPS parameters it does not support, so an unsupported
    // option fails quietly rather than loudly. Keep this request boring.
    const completion = await client.chat.completions.create({
      model: MODEL,
      messages: [{ role: "system", content: SYSTEM_PROMPT }, ...messages],
    });

    const reply = completion.choices?.[0]?.message?.content;
    if (!reply) {
      return res
        .status(502)
        .json({ error: "The model returned an empty response." });
    }
    res.json({ reply });
  } catch (err) {
    // Full detail to the server log, sanitised message to the browser.
    console.error("Upstream error:", err?.status, err?.message);
    const { status, error } = describeUpstreamError(err);
    res.status(status).json({ error });
  }
});

// Render pings a health check; this also gives you a fast way to confirm which
// model a deploy is actually running without opening the dashboard.
app.get("/healthz", (_req, res) => res.json({ ok: true, model: MODEL }));

app.use(express.static(join(__dirname, "public")));

// Render assigns the port and health-checks it. Hardcoding a port, or binding
// localhost instead of 0.0.0.0, is the single most common cause of a Node
// service that builds fine and then never goes live.
const PORT = process.env.PORT || 3000;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Listening on :${PORT} — model ${MODEL}`);
});
