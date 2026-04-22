"""
artifact_crypto.py
Encrypts and decrypts PPLLM chunk JSON artifacts using RSA + AES hybrid encryption.

How it works (mirrors HTTPS/TLS):
  1. A random AES-256 key is generated for each file (fast symmetric encryption)
  2. The AES key is encrypted with the RSA public key (slow but secure key exchange)
  3. The file is encrypted with AES-GCM (authenticated encryption — detects tampering)
  4. Everything is bundled into a single .enc file

To decrypt:
  1. The RSA private key decrypts the AES key
  2. The AES key decrypts the file content
  3. Original chunk JSON is restored
"""

import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from encryption.key_manager import load_keys

ENCRYPTED_DIR = Path.home() / "Documents" / "LLM_Bundler" / "encrypted"


def encrypt_artifact(chunk_path: str | Path, output_dir: Path = ENCRYPTED_DIR) -> Path:
    """
    Encrypt a chunk JSON artifact using RSA + AES-256-GCM hybrid encryption.

    Args:
        chunk_path: Path to the chunk JSON file to encrypt
        output_dir: Directory to save the encrypted .enc file

    Returns:
        Path to the encrypted .enc file
    """
    chunk_path = Path(chunk_path)
    if not chunk_path.exists():
        raise FileNotFoundError(f"Chunk file not found: {chunk_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load RSA public key
    _, public_key = load_keys()

    # Read chunk JSON content
    plaintext = chunk_path.read_bytes()

    # Generate a random 256-bit AES key and 96-bit nonce
    aes_key = os.urandom(32)
    nonce = os.urandom(12)

    # Encrypt the file content with AES-256-GCM
    aesgcm = AESGCM(aes_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # Encrypt the AES key with RSA public key (OAEP padding — same as TLS)
    encrypted_aes_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # Bundle: [4 bytes: len of encrypted_aes_key] + [encrypted_aes_key] + [nonce] + [ciphertext]
    enc_key_len = len(encrypted_aes_key).to_bytes(4, byteorder="big")
    bundle = enc_key_len + encrypted_aes_key + nonce + ciphertext

    # Save encrypted file
    output_path = output_dir / (chunk_path.stem + ".enc")
    output_path.write_bytes(bundle)

    print(f"[artifact_crypto] Encrypted: {chunk_path.name} → {output_path}")
    return output_path


def decrypt_artifact(enc_path: str | Path, output_dir: Path = None) -> Path:
    """
    Decrypt an encrypted .enc artifact back to the original chunk JSON.

    Args:
        enc_path: Path to the .enc encrypted file
        output_dir: Directory to save the decrypted JSON (defaults to same dir as .enc file)

    Returns:
        Path to the decrypted JSON file
    """
    enc_path = Path(enc_path)
    if not enc_path.exists():
        raise FileNotFoundError(f"Encrypted file not found: {enc_path}")

    if output_dir is None:
        output_dir = enc_path.parent

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load RSA private key
    private_key, _ = load_keys()

    # Read encrypted bundle
    bundle = enc_path.read_bytes()

    # Unpack: [4 bytes: len] + [encrypted_aes_key] + [12 bytes nonce] + [ciphertext]
    enc_key_len = int.from_bytes(bundle[:4], byteorder="big")
    encrypted_aes_key = bundle[4: 4 + enc_key_len]
    nonce = bundle[4 + enc_key_len: 4 + enc_key_len + 12]
    ciphertext = bundle[4 + enc_key_len + 12:]

    # Decrypt AES key with RSA private key
    aes_key = private_key.decrypt(
        encrypted_aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # Decrypt file content with AES-256-GCM
    aesgcm = AESGCM(aes_key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    # Save decrypted JSON
    output_path = output_dir / (enc_path.stem + "_decrypted.json")
    output_path.write_bytes(plaintext)

    print(f"[artifact_crypto] Decrypted: {enc_path.name} → {output_path}")
    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python artifact_crypto.py encrypt <chunk_json_path>")
        print("       python artifact_crypto.py decrypt <enc_file_path>")
        sys.exit(1)

    command = sys.argv[1]
    target = sys.argv[2]

    if command == "encrypt":
        result = encrypt_artifact(target)
        print(f"Encrypted file saved to: {result}")
    elif command == "decrypt":
        result = decrypt_artifact(target)
        print(f"Decrypted file saved to: {result}")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
