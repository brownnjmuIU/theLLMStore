import type { ExtractionResult } from '../core/types';

/**
 * Port of extractors/platform_extractor.py.
 *
 * Pure logic with no external parser, so unlike PDF and DOCX this one CAN be
 * held to exact conformance with Python.
 *
 * ONE KNOWN DIVERGENCE, unavoidable without a custom JSON parser:
 * Python distinguishes int from float, so `{"score": 1.0}` renders as
 * "score: 1.0". JavaScript's JSON.parse collapses both to the same number, so it
 * renders "score: 1". Integers, strings, booleans, null and nesting all match
 * exactly. Whole-number floats are the only case that differs.
 */

const LIST_CAP = 200;
const MAX_LINES = 1000;

/**
 * Python's str() for scalars. Differs from JavaScript's String() for three of the
 * four JSON scalar types, which is why this exists rather than inlining String().
 */
function pythonStr(value: unknown): string {
  if (value === null) return 'None';
  if (value === true) return 'True';
  if (value === false) return 'False';
  return String(value);
}

/** Port of _flatten_json. Returns "key.path[0]: value" lines. */
export function flattenJson(obj: unknown, prefix = ''): string[] {
  const lines: string[] = [];

  if (Array.isArray(obj)) {
    obj.slice(0, LIST_CAP).forEach((value, i) => {
      lines.push(...flattenJson(value, `${prefix}[${i}]`));
    });
    if (obj.length > LIST_CAP) {
      lines.push(`${prefix}: [truncated list, total items=${obj.length}]`);
    }
  } else if (obj !== null && typeof obj === 'object') {
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      lines.push(...flattenJson(value, prefix ? `${prefix}.${key}` : String(key)));
    }
  } else {
    lines.push(`${prefix}: ${pythonStr(obj)}`);
  }

  return lines;
}

export function extractTextFromPlatformExport(fileBytes: Uint8Array): ExtractionResult {
  const lines: string[] = ['Platform Export Data'];
  lines.push(`File Size (bytes): ${fileBytes.byteLength}`);

  let data: unknown;
  try {
    // TextDecoder with BOM stripping mirrors Python's utf-8 -> utf-8-sig fallback.
    const text = new TextDecoder('utf-8').decode(fileBytes).replace(/^﻿/, '');
    data = JSON.parse(text);
  } catch (error) {
    lines.push('');
    lines.push('JSON Parse Error:');
    lines.push(error instanceof Error ? error.message : String(error));
    return { text: lines.join('\n').trim(), page_count: null };
  }

  lines.push('');
  // Python reports type(data).__name__ — dict / list / str / int.
  const typeName = Array.isArray(data)
    ? 'list'
    : data === null
      ? 'NoneType'
      : typeof data === 'object'
        ? 'dict'
        : typeof data === 'string'
          ? 'str'
          : typeof data === 'boolean'
            ? 'bool'
            : 'int';
  lines.push(`Top-level Type: ${typeName}`);

  if (typeName === 'dict') {
    const keys = Object.keys(data as Record<string, unknown>).slice(0, 50);
    lines.push(`Top-level Keys: ${keys.join(', ')}`);
  } else if (Array.isArray(data)) {
    lines.push(`Top-level List Length: ${data.length}`);
  }

  lines.push('');
  lines.push('Flattened Behavioral Data (MVP):');

  const flattened = flattenJson(data);
  if (flattened.length === 0) {
    lines.push('[No readable fields found]');
  } else {
    lines.push(...flattened.slice(0, MAX_LINES));
    if (flattened.length > MAX_LINES) {
      lines.push(
        `[truncated flattened output: showing ${MAX_LINES} of ${flattened.length} lines]`
      );
    }
  }

  return { text: lines.join('\n').trim(), page_count: null };
}
