import io
from PIL import Image, ExifTags


def extract_text_from_image(file_bytes: bytes) -> dict:
    """
    Extract image metadata (and optionally OCR later) from image bytes.
    Returns dict with text and page_count for compatibility with existing pipeline.
    """
    img = Image.open(io.BytesIO(file_bytes))

    lines = []
    lines.append("Image File")
    lines.append(f"Format: {img.format}")
    lines.append(f"Mode: {img.mode}")
    lines.append(f"Size: {img.width}x{img.height}")

    # EXIF metadata (if present, common in JPEGs)
    exif = getattr(img, "getexif", lambda: None)()
    if exif:
        lines.append("")
        lines.append("EXIF Metadata:")
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            try:
                lines.append(f"{tag_name}: {value}")
            except Exception:
                lines.append(f"{tag_name}: [unreadable]")

    # OCR placeholder for now (add later once pytesseract is confirmed)
    lines.append("")
    lines.append("OCR Text:")
    lines.append("[OCR not enabled in this build yet]")

    return {
        "text": "\n".join(lines).strip(),
        "page_count": None
    }
