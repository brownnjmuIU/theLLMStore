/**
 * Port of the sensitive-filename heuristic in desktop_app.py lines 480-496.
 *
 * Substring match on the FILENAME only — it never opens the file. Same six
 * keywords as the desktop app, kept identical on purpose: if the two versions
 * warned about different files, the comparison between them would be muddied.
 *
 * Its weakness is worth being honest about in the UI rather than hiding: naming
 * a file `vacation.pdf` bypasses it entirely. That is a teaching opportunity, not
 * something to paper over.
 */

export const SENSITIVE_KEYWORDS = [
  'private',
  'secret',
  'password',
  'bank',
  'ssn',
  'confidential',
] as const;

export function isSensitiveFilename(filename: string): boolean {
  const lower = filename.toLowerCase();
  return SENSITIVE_KEYWORDS.some((keyword) => lower.includes(keyword));
}

export function matchedKeywords(filename: string): string[] {
  const lower = filename.toLowerCase();
  return SENSITIVE_KEYWORDS.filter((keyword) => lower.includes(keyword));
}
