import io
from PIL import Image, ExifTags
import pytesseract


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

    ocr_text = ""
    ocr_error = None
    try:
        ocr_text = pytesseract.image_to_string(img) or ""
    except Exception as e:
        ocr_text = ""
        ocr_error = str(e)

    lines.append("")
    lines.append("OCR Text:")
    lines.append(ocr_text.strip() if ocr_text.strip() else "[No OCR text detected]")
    if ocr_error:
        lines.append(f"OCR Error: {ocr_error}")

    return {
        "text": "\n".join(lines).strip(),
        "page_count": None,
        "ocr_text": ocr_text.strip()
    }
