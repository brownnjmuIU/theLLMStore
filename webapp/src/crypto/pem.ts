/**
 * PEM <-> DER conversion.
 *
 * Web Crypto speaks DER (SPKI for public keys, PKCS8 for private). Python's
 * `cryptography` library writes PEM — base64-wrapped DER with header and footer
 * lines. Converting between them is what makes keys interoperable between the
 * browser port and the desktop app.
 */

const LINE_LENGTH = 64;

function toBase64(bytes: ArrayBuffer): string {
  const view = new Uint8Array(bytes);
  let binary = '';
  // Chunked to avoid blowing the argument limit on large keys.
  for (let i = 0; i < view.length; i += 0x8000) {
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

function fromBase64(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

export function derToPem(der: ArrayBuffer, label: 'PUBLIC KEY' | 'PRIVATE KEY'): string {
  const base64 = toBase64(der);
  const lines: string[] = [];
  for (let i = 0; i < base64.length; i += LINE_LENGTH) {
    lines.push(base64.slice(i, i + LINE_LENGTH));
  }
  // Trailing newline matches what Python's cryptography writes.
  return `-----BEGIN ${label}-----\n${lines.join('\n')}\n-----END ${label}-----\n`;
}

export function pemToDer(pem: string): ArrayBuffer {
  const body = pem
    .replace(/-----BEGIN [^-]+-----/, '')
    .replace(/-----END [^-]+-----/, '')
    .replace(/\s+/g, '');
  return fromBase64(body);
}
