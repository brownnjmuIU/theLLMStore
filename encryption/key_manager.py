"""
key_manager.py
Generates and loads RSA public/private key pairs for PPLLM artifact encryption.

Keys are saved to ~/Documents/LLM_Bundler/keys/ by default.
- private_key.pem  : keep this secret, never share
- public_key.pem   : share with the intended recipient (e.g. cloud platform)
"""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KEYS_DIR = Path.home() / "Documents" / "LLM_Bundler" / "keys"


def generate_keys(keys_dir: Path = KEYS_DIR) -> tuple[Path, Path]:
    """
    Generate a new RSA 2048-bit key pair and save to disk.
    Returns (private_key_path, public_key_path).
    Skips generation if keys already exist.
    """
    keys_dir.mkdir(parents=True, exist_ok=True)
    private_key_path = keys_dir / "private_key.pem"
    public_key_path = keys_dir / "public_key.pem"

    if private_key_path.exists() and public_key_path.exists():
        print(f"[key_manager] Keys already exist at {keys_dir} — skipping generation.")
        return private_key_path, public_key_path

    # Generate RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Save private key (PEM, unencrypted for MVP)
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    # Save public key (PEM)
    public_key_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    print(f"[key_manager] Keys generated and saved to {keys_dir}")
    return private_key_path, public_key_path


def load_keys(keys_dir: Path = KEYS_DIR):
    """
    Load existing RSA key pair from disk.
    Returns (private_key, public_key) objects.
    Raises FileNotFoundError if keys do not exist — run generate_keys() first.
    """
    private_key_path = keys_dir / "private_key.pem"
    public_key_path = keys_dir / "public_key.pem"

    if not private_key_path.exists() or not public_key_path.exists():
        raise FileNotFoundError(
            f"Keys not found at {keys_dir}. Run generate_keys() first."
        )

    private_key = serialization.load_pem_private_key(
        private_key_path.read_bytes(),
        password=None,
    )
    public_key = serialization.load_pem_public_key(
        public_key_path.read_bytes()
    )

    return private_key, public_key


if __name__ == "__main__":
    priv, pub = generate_keys()
    print(f"Private key: {priv}")
    print(f"Public key:  {pub}")
