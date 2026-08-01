/**
 * Port of encryption/artifact_crypto.py — RSA + AES-256-GCM hybrid encryption.
 *
 * The wire format is reproduced EXACTLY so a .enc file produced here decrypts
 * with `python -m encryption.artifact_crypto decrypt`, and vice versa:
 *
 *   ┌────────┬──────────────────┬─────────┬───────────────────────┐
 *   │ 4 bytes│ RSA-wrapped AES  │ 12 bytes│ ciphertext ‖ GCM tag  │
 *   │ keylen │ key (256 for 2k) │  nonce  │      (tag = 16 B)     │
 *   │ big-end│                  │         │                       │
 *   └────────┴──────────────────┴─────────┴───────────────────────┘
 *
 * Why hybrid: RSA-2048 with OAEP/SHA-256 can only encrypt 190 bytes and is slow.
 * AES handles any size but needs a shared key. So the data is encrypted with a
 * fresh AES key, and that key is wrapped with RSA — the same construction TLS uses.
 *
 * A fresh key AND nonce per artifact makes nonce reuse — GCM's one catastrophic
 * failure mode — structurally impossible.
 */

const NONCE_BYTES = 12;
const AES_KEY_BITS = 256;

export interface EncryptResult {
  bytes: Uint8Array;
  filename: string;
}

export async function encryptArtifact(
  json: string,
  publicKey: CryptoKey,
  sourceFilename: string
): Promise<EncryptResult> {
  const plaintext = new TextEncoder().encode(json);

  const aesKey = await crypto.subtle.generateKey({ name: 'AES-GCM', length: AES_KEY_BITS }, true, [
    'encrypt',
  ]);
  const nonce = crypto.getRandomValues(new Uint8Array(NONCE_BYTES));

  // Web Crypto returns ciphertext ‖ tag concatenated, exactly as Python's
  // AESGCM.encrypt does — so no reassembly is needed.
  const ciphertext = new Uint8Array(
    await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce }, aesKey, plaintext)
  );

  const rawAesKey = await crypto.subtle.exportKey('raw', aesKey);
  const wrappedKey = new Uint8Array(
    await crypto.subtle.encrypt({ name: 'RSA-OAEP' }, publicKey, rawAesKey)
  );

  const header = new Uint8Array(4);
  new DataView(header.buffer).setUint32(0, wrappedKey.length, false); // big-endian

  const bundle = new Uint8Array(
    header.length + wrappedKey.length + nonce.length + ciphertext.length
  );
  let offset = 0;
  bundle.set(header, offset);
  offset += header.length;
  bundle.set(wrappedKey, offset);
  offset += wrappedKey.length;
  bundle.set(nonce, offset);
  offset += nonce.length;
  bundle.set(ciphertext, offset);

  return {
    bytes: bundle,
    // Matches Python: chunk_path.stem + ".enc"
    filename: `${sourceFilename.replace(/\.json$/, '')}.enc`,
  };
}

export async function decryptArtifact(bundle: Uint8Array, privateKey: CryptoKey): Promise<string> {
  if (bundle.length < 4) throw new Error('Encrypted file is truncated');

  const view = new DataView(bundle.buffer, bundle.byteOffset, bundle.byteLength);
  const keyLength = view.getUint32(0, false);

  if (bundle.length < 4 + keyLength + NONCE_BYTES) {
    throw new Error('Encrypted file is truncated or not a PPLLM artifact');
  }

  // slice() rather than subarray(): it copies into a fresh ArrayBuffer, which
  // both satisfies Web Crypto's BufferSource typing and avoids handing the
  // crypto layer views that alias the caller's buffer.
  const wrappedKey = bundle.slice(4, 4 + keyLength);
  const nonce = bundle.slice(4 + keyLength, 4 + keyLength + NONCE_BYTES);
  const ciphertext = bundle.slice(4 + keyLength + NONCE_BYTES);

  const rawAesKey = await crypto.subtle.decrypt({ name: 'RSA-OAEP' }, privateKey, wrappedKey);
  const aesKey = await crypto.subtle.importKey('raw', rawAesKey, { name: 'AES-GCM' }, false, [
    'decrypt',
  ]);

  // Throws if the GCM tag does not verify — i.e. the file was tampered with.
  const plaintext = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce }, aesKey, ciphertext);

  return new TextDecoder().decode(plaintext);
}
