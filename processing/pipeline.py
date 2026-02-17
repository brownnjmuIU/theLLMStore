from storage.json_store import load_raw_document_by_path, save_chunks
from processing.cleaner import clean_text
from processing.chunker import chunk_text


def process_document(
    file_path: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100
) -> dict:
    """
    Stage 4 Pipeline: Load → Clean → Chunk → Save

    Args:
        file_path: Path to Stage 3 JSON artifact
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        Chunk data structure (also saved to disk)
    """
    # 1. Loading Stage 3 artifact from disk
    doc = load_raw_document_by_path(file_path)
    if doc is None:
        raise ValueError(f"Document not found: {file_path}")

    # 2. Extract raw text field
    raw_text = doc["text"]

    # 3. Cleaning text (deterministic normalization)
    cleaned_text = clean_text(raw_text)

    # 4. Chunking cleaned text
    chunks_data = chunk_text(
        text=cleaned_text,
        doc_id=doc["doc_id"],
        source_filename=doc["source_filename"],
        file_type=doc["file_type"],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    # 5. Saving chunks to disk
    output_path = save_chunks(chunks_data)
    chunks_data["output_path"] = output_path

    return chunks_data
