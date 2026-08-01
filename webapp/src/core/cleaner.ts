/**
 * Port of processing/cleaner.py::clean_text.
 *
 * Seven order-dependent operations. The order is load-bearing — see step 1.
 *
 * Three places where a naive port silently diverges from Python, each covered by
 * a conformance fixture:
 *
 *   - Python's \w is Unicode-aware; JavaScript's is [A-Za-z0-9_].      (fixture 004)
 *   - Python's \s covers a slightly different set than JavaScript's.   (fixture 010)
 *   - Python's str.strip() strips a different set than JS trim().      (fixture 011)
 *
 * So the whitespace and word classes below are written out explicitly rather than
 * using \s and \w. That is deliberate: it is the only way to guarantee the two
 * implementations agree.
 */

import { pyStrip } from './pythonCompat';

/** Python's \s minus \n and \t — i.e. the `[^\S\n\t]` in cleaner.py step 3. */
const HORIZONTAL_WHITESPACE = new RegExp(
  `[ \\r\\f\\v\\x1c-\\x1f\\x85\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]+`,
  'gu'
);

/**
 * Python's \w: alphanumeric per str.isalnum(), plus underscore.
 * Maps to Unicode letter + number categories. JavaScript's \w would only match
 * [A-Za-z0-9_] and would leave `Café-\nübernahme` unjoined.
 */
const HYPHEN_LINEBREAK = /([\p{L}\p{N}_])-\n([\p{L}\p{N}_])/gu;

/** Keep printable ASCII, newline, tab, and U+00A0–U+FFFF. Everything else goes. */
const NON_PRINTABLE = /[^\x20-\x7E\n\t -￿]/gu;

const THREE_PLUS_NEWLINES = /\n{3,}/gu;

export function cleanText(text: string): string {
  // 1. Normalise line endings.
  //    MUST run before dehyphenation: the (\w)-\n(\w) pattern cannot match CRLF
  //    input, so reversing these two silently disables dehyphenation for every
  //    Windows-authored document. Fixtures 002 and 003 lock this in.
  let result = text.replaceAll('\r\n', '\n').replaceAll('\r', '\n');

  // 2. Rejoin words broken across a line by a hyphen.
  result = result.replace(HYPHEN_LINEBREAK, '$1$2');

  // 3. Collapse runs of horizontal whitespace to a single space.
  //    Also collapses NBSP, which Python's \s matches.
  result = result.replace(HORIZONTAL_WHITESPACE, ' ');

  // 4. Strip control characters and astral characters.
  //    Runs AFTER step 3, so spaces that surrounded a removed emoji remain —
  //    producing a double space. Fixture 005 depends on that.
  result = result.replace(NON_PRINTABLE, '');

  // 5. Collapse three or more newlines into a paragraph break.
  result = result.replace(THREE_PLUS_NEWLINES, '\n\n');

  // 6. Trim each line.
  result = result.split('\n').map(pyStrip).join('\n');

  // 7. Trim the whole string.
  return pyStrip(result);
}
