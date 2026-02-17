from docx import Document
import io

def extract_text_from_docx(file_bytes: bytes) -> dict:
    """
    Extract text from DOCX bytes.
    Returns dict with text and page_count.
    """
    doc = Document(io.BytesIO(file_bytes))

    paragraphs_text = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            paragraphs_text.append(paragraph.text)

    full_text = "\n\n".join(paragraphs_text)

    return {
        "text": full_text.strip(),
        "page_count": None
    }