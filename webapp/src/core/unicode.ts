/**
 * Code-point helpers — the guardrail against the port's most dangerous class of bug.
 *
 * Python strings are sequences of CODE POINTS. JavaScript strings are sequences of
 * UTF-16 CODE UNITS. For any character above U+FFFF (emoji, supplementary CJK,
 * mathematical alphanumerics) they disagree, and one code point becomes two units.
 *
 * Consequences if this is ignored:
 *   - `text.slice(0, 500)` selects a different substring than Python's `text[:500]`,
 *     producing a DIFFERENT doc_id for the same file.
 *   - `text.length` reports a different size than Python's `len(text)`, so
 *     chunk_size=800 means something different and every boundary shifts.
 *
 * Conformance fixtures 005 and 012 exist specifically to catch this, and their
 * meta.json records both lengths so the disagreement is visible.
 *
 * RULE: inside src/core/, never use .length or [i] on user text. Use these.
 */

/** Split into code points — what Python iteration over a str yields. */
export function toCodePoints(text: string): string[] {
  return Array.from(text);
}

/** Length in code points — equivalent to Python's `len(text)`. */
export function codePointLength(text: string): number {
  return Array.from(text).length;
}

/** Slice by code point — equivalent to Python's `text[start:end]`. */
export function sliceCodePoints(text: string, start: number, end?: number): string {
  return Array.from(text).slice(start, end).join('');
}

/** Length in UTF-16 units — what JavaScript's `.length` reports. Diagnostic only. */
export function utf16Length(text: string): number {
  return text.length;
}

/** True when the two measures disagree, i.e. the text contains astral characters. */
export function hasAstralCharacters(text: string): boolean {
  return text.length !== codePointLength(text);
}
