import os
import sqlite3
import tempfile


def extract_text_from_browser_history(file_bytes: bytes) -> dict:
    """
    Extract browsing history-like records from a browser SQLite DB copy.

    Returns dict with text and page_count for compatibility with existing pipeline.
    Notes:
    - Designed for local copies/exports of browser history SQLite databases.
    - MVP focuses on common Chrome-style schema (`urls` table).
    """
    lines = ["Browser History Data"]
    lines.append(f"File Size (bytes): {len(file_bytes)}")

    temp_path = None
    conn = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite") as tmp:
            tmp.write(file_bytes)
            temp_path = tmp.name

        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT url, title, last_visit_time, visit_count
            FROM urls
            ORDER BY last_visit_time DESC
            LIMIT 200
            """
        )
        rows = cursor.fetchall()

        lines.append("")
        lines.append(f"Records Extracted: {len(rows)}")
        lines.append("")

        if not rows:
            lines.append("[No rows found in `urls` table]")
        else:
            for i, (url, title, last_visit_time, visit_count) in enumerate(rows, start=1):
                lines.append(f"Record {i}")
                lines.append(f"URL: {url or ''}")
                lines.append(f"Title: {title or ''}")
                lines.append(f"Visit Count: {visit_count or 0}")
                lines.append(f"Last Visit Time (raw): {last_visit_time or ''}")
                lines.append("")

    except sqlite3.Error as exc:
        lines.append("")
        lines.append("SQLite Parse Error:")
        lines.append(str(exc))
        lines.append("")
        lines.append("Note: This file may not be a Chrome-style history DB or may use a different schema.")
    except Exception as exc:
        lines.append("")
        lines.append("Browser History Extraction Error:")
        lines.append(str(exc))
    finally:
        if conn is not None:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    return {"text": "\n".join(lines).strip(), "page_count": None}
