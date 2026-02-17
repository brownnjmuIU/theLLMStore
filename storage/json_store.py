import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Base directory for all outputs — resolves to user's Documents folder
BASE_DIR = Path.home() / "Documents" / "LLM_Bundler" / "outputs"
RAW_DIR = BASE_DIR / "raw"
CHUNKS_DIR = BASE_DIR / "chunks"


def get_output_root() -> Path:
    """Return the root output directory (used by app.py for display)."""
    return BASE_DIR


def generate_doc_id(filename: str, text: str) -> str:
    """Generate stable 8-char document ID."""
    content = f"{filename}:{text[:500]}"
    return hashlib.sha256(content.encode()).hexdigest()[:8]

def save_artifact(
    filename: str,
    file_type: str,
    text: str,
    page_count: int | None,
    output_dir: Path = RAW_DIR
) -> tuple[str, str]:
    """
    Save extracted raw text as JSON artifact.
    Returns (doc_id, file_path).
    """
    os.makedirs(output_dir, exist_ok=True)

    doc_id = generate_doc_id(filename, text)

    artifact = {
        "doc_id": doc_id,
        "source_filename": filename,
        "file_type": file_type,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "page_count": page_count,
        "text": text
    }

    output_path = output_dir / f"doc_{doc_id}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)

    return doc_id, str(output_path)


def load_raw_document_by_path(file_path: str) -> dict | None:
    """
    Load a raw document by file path.
    Generates doc_id if missing (backwards compatibility).
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    # Backwards compatibility: generate doc_id if missing
    if "doc_id" not in doc:
        doc["doc_id"] = generate_doc_id(doc["source_filename"], doc["text"])
    
    # Normalize key names
    if "extracted_at" in doc and "ingested_at" not in doc:
        doc["ingested_at"] = doc["extracted_at"]

    return doc


def list_raw_documents(output_dir: Path = RAW_DIR) -> list[dict]:
    """
    List all raw documents (metadata only).
    Searches RAW_DIR by default.
    """
    documents = []

    if not output_dir.exists():
        return documents

    for filename in output_dir.iterdir():
        if filename.suffix == ".json" and not filename.name.endswith("_chunks.json"):
            doc = load_raw_document_by_path(str(filename))
            if doc:
                documents.append({
                    "doc_id": doc["doc_id"],
                    "source_filename": doc["source_filename"],
                    "file_type": doc["file_type"],
                    "ingested_at": doc.get("ingested_at", doc.get("extracted_at")),
                    "page_count": doc.get("page_count"),
                    "text_length": len(doc["text"]),
                    "file_path": str(filename)
                })

    return sorted(documents, key=lambda x: x["ingested_at"], reverse=True)

def save_chunks(chunks_data: dict, output_dir: Path = CHUNKS_DIR) -> str:
    """Save chunked document as JSON."""
    if "doc_id" not in chunks_data:
        raise ValueError("chunks_data must contain doc_id")

    os.makedirs(output_dir, exist_ok=True)

    doc_id = chunks_data["doc_id"]
    output_path = output_dir / f"doc_{doc_id}_chunks.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)

    return str(output_path)


def load_chunks(doc_id: str, output_dir: Path = CHUNKS_DIR) -> dict | None:
    """Load chunks by doc_id."""
    file_path = output_dir / f"doc_{doc_id}_chunks.json"

    if not file_path.exists():
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    