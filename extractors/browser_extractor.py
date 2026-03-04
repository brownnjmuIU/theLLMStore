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


def extract_text_from_browser_cookies(file_bytes: bytes) -> dict:
    """
    Extract non-sensitive cookie metadata from a browser SQLite DB copy.

    Returns dict with text and page_count for compatibility with existing pipeline.
    Security:
    - Intentionally excludes cookie values (`value`, `encrypted_value`).
    - Designed for Chrome-style cookies schema.
    """
    lines = ["Browser Cookie Data (Safe Fields Only)"]
    lines.append(f"File Size (bytes): {len(file_bytes)}")

    temp_path = None
    conn = None
    cookie_records = []

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite") as tmp:
            tmp.write(file_bytes)
            temp_path = tmp.name

        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                host_key,
                name,
                path,
                expires_utc,
                is_secure,
                is_httponly,
                last_access_utc,
                has_expires,
                is_persistent,
                priority
            FROM cookies
            ORDER BY last_access_utc DESC
            LIMIT 1000
            """
        )
        rows = cursor.fetchall()

        lines.append("")
        lines.append(f"Records Extracted: {len(rows)}")
        lines.append("")

        if not rows:
            lines.append("[No rows found in `cookies` table]")
        else:
            for i, row in enumerate(rows, start=1):
                record = {
                    "host_key": row[0] or "",
                    "name": row[1] or "",
                    "path": row[2] or "",
                    "expires_utc": row[3] or "",
                    "is_secure": int(row[4]) if row[4] is not None else 0,
                    "is_httponly": int(row[5]) if row[5] is not None else 0,
                    "last_access_utc": row[6] or "",
                    "has_expires": int(row[7]) if row[7] is not None else 0,
                    "is_persistent": int(row[8]) if row[8] is not None else 0,
                    "priority": row[9] if row[9] is not None else "",
                }
                cookie_records.append(record)

                lines.append(f"Record {i}")
                lines.append(f"Domain: {record['host_key']}")
                lines.append(f"Cookie Name: {record['name']}")
                lines.append(f"Path: {record['path']}")
                lines.append(f"Secure: {record['is_secure']}")
                lines.append(f"HttpOnly: {record['is_httponly']}")
                lines.append(f"Last Access Time (raw): {record['last_access_utc']}")
                lines.append(f"Expires Time (raw): {record['expires_utc']}")
                lines.append(f"Has Expires: {record['has_expires']}")
                lines.append(f"Is Persistent: {record['is_persistent']}")
                lines.append(f"Priority: {record['priority']}")
                lines.append("")

    except sqlite3.Error as exc:
        lines.append("")
        lines.append("SQLite Parse Error:")
        lines.append(str(exc))
        lines.append("")
        lines.append("Note: This file may not be a Chrome-style cookies DB or may use a different schema.")
    except Exception as exc:
        lines.append("")
        lines.append("Browser Cookie Extraction Error:")
        lines.append(str(exc))
    finally:
        if conn is not None:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "text": "\n".join(lines).strip(),
        "page_count": None,
        "cookie_records": cookie_records,
    }
