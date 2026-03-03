import json


def _flatten_json(obj, prefix=""):
    """
    Flatten nested JSON into key-path + value lines.
    Returns a list of strings.
    """
    lines = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(_flatten_json(value, new_prefix))
    elif isinstance(obj, list):
        for i, value in enumerate(obj[:200]):  # cap to avoid huge outputs in MVP
            new_prefix = f"{prefix}[{i}]"
            lines.extend(_flatten_json(value, new_prefix))
        if len(obj) > 200:
            lines.append(f"{prefix}: [truncated list, total items={len(obj)}]")
    else:
        safe_value = str(obj)
        lines.append(f"{prefix}: {safe_value}")

    return lines


def extract_text_from_platform_export(file_bytes: bytes) -> dict:
    """
    Extract readable text from platform JSON export data (Google/Meta/etc.).
    Returns dict with text and page_count for compatibility with existing pipeline.
    """
    lines = ["Platform Export Data"]
    lines.append(f"File Size (bytes): {len(file_bytes)}")

    try:
        data = json.loads(file_bytes.decode("utf-8"))
    except UnicodeDecodeError:
        try:
            data = json.loads(file_bytes.decode("utf-8-sig"))
        except Exception as exc:
            lines.append("")
            lines.append("Decode Error:")
            lines.append(str(exc))
            return {"text": "\n".join(lines).strip(), "page_count": None}
    except Exception as exc:
        lines.append("")
        lines.append("JSON Parse Error:")
        lines.append(str(exc))
        return {"text": "\n".join(lines).strip(), "page_count": None}

    lines.append("")
    lines.append(f"Top-level Type: {type(data).__name__}")

    if isinstance(data, dict):
        lines.append(f"Top-level Keys: {', '.join(list(data.keys())[:50])}")
    elif isinstance(data, list):
        lines.append(f"Top-level List Length: {len(data)}")

    lines.append("")
    lines.append("Flattened Behavioral Data (MVP):")

    flattened = _flatten_json(data)
    if not flattened:
        lines.append("[No readable fields found]")
    else:
        max_lines = 1000
        for line in flattened[:max_lines]:
            lines.append(line)
        if len(flattened) > max_lines:
            lines.append(f"[truncated flattened output: showing {max_lines} of {len(flattened)} lines]")

    return {"text": "\n".join(lines).strip(), "page_count": None}
