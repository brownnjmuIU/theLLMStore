/**
 * Python string semantics that JavaScript does not match.
 *
 * Shared by cleaner.ts and chunker.ts. Kept in one place because a divergence
 * here shifts every chunk boundary, and the two modules must agree.
 */

/**
 * Python's `\s` for str values: ASCII whitespace, the C0 separators \x1c-\x1f,
 * NEL (\x85), and the Unicode space separators.
 *
 * Differs from JavaScript's `\s` in BOTH directions — JS includes ﻿ (U+FEFF)
 * and excludes \x1c-\x1f and \x85 — which is why this is written out rather than
 * using `\s`.
 */
export const PY_WHITESPACE =
  ' \\t\\n\\r\\f\\v\\x1c-\\x1f\\x85\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';

const TRIM_PATTERN = new RegExp(`^[${PY_WHITESPACE}]+|[${PY_WHITESPACE}]+$`, 'gu');

/**
 * Equivalent to Python's `str.strip()`.
 *
 * JavaScript's `.trim()` strips a different set, so using it would diverge on
 * text containing U+FEFF or the C0 separators.
 */
export function pyStrip(text: string): string {
  return text.replace(TRIM_PATTERN, '');
}
