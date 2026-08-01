import { sliceCodePoints } from './unicode';

/**
 * Port of storage/json_store.py::generate_doc_id.
 *
 * Python:
 *     content = f"{filename}:{text[:500]}"
 *     return hashlib.sha256(content.encode()).hexdigest()[:8]
 *
 * Two things that would silently break parity:
 *
 *  1. `text[:500]` slices 500 CODE POINTS. Using `.slice(0, 500)` here would slice
 *     500 UTF-16 units and produce a different string — and therefore a different
 *     hash — for any text with astral characters near the boundary. Fixture 012 is
 *     engineered to fail if that happens.
 *
 *  2. The trailing `[:8]` truncates the HEX STRING to 8 characters (4 bytes), not
 *     the digest to 8 bytes.
 *
 * Async because Web Crypto's digest() returns a Promise. Available as
 * globalThis.crypto.subtle in Node 18+ and every target browser, so this same code
 * runs in tests and in the app.
 */
export async function generateDocId(filename: string, text: string): Promise<string> {
  const content = `${filename}:${sliceCodePoints(text, 0, 500)}`;
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(content));

  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, 8);
}
