import fitz  # pymupdf


def extract_text_from_pdf(file_bytes: bytes) -> dict:
    """
    Extract text from PDF bytes.
    Returns dict with text and page_count.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    
    full_text = "\n\n".join(pages_text)
    page_count = len(doc)
    doc.close()
    
    return {
        "text": full_text.strip(),
        "page_count": page_count
    }