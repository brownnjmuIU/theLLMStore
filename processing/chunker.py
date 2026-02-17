from datetime import datetime, timezone
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    text: str,
    doc_id: str,
    source_filename: str,
    file_type: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100
) -> dict:
    """
    Split text into chunks using RecursiveCharacterTextSplitter.
    
    Args:
        text:  Pre-cleaned text from stored document
        doc_id: Stable document ID (passed in, NOT generated)
        source_filename: Original filename
        file_type: File type (pdf, docx, pptx)
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
    
    Returns:
        Chunk data structure ready for storage
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", ", ", " ", ""]
    )
    
    chunks = splitter.split_text(text)
    
    chunk_list = []    
    current_pos = 0

    for i, chunk_text in enumerate(chunks):
        chunk_start = current_pos
        chunk_end = chunk_start + len(chunk_text)

        chunk_list.append({
            "chunk_id": f"{doc_id}_{i+1:04d}",
            "chunk_index": i + 1,
            "char_start": chunk_start,
            "char_end": chunk_end,
            "text": chunk_text
        })

        current_pos = chunk_end - chunk_overlap
        if current_pos < 0:
            current_pos = 0
        
    
    return {
        "doc_id": doc_id,
        "source_filename": source_filename,
        "file_type": file_type,
        "total_chunks": len(chunks),
        "chunked_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "splitter": "RecursiveCharacterTextSplitter"
        },
        "chunks": chunk_list
    }
