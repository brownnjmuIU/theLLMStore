import os
import sys
import time
import threading
import webbrowser
import urllib.request
from pathlib import Path

import streamlit.web.bootstrap as bootstrap

PORT = 8501
URL = f"http://localhost:{PORT}"


def resource_path(rel_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel_path


def wait_for_server(timeout: int = 60) -> bool:
    health_url = f"{URL}/_stcore/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(health_url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def open_browser_when_ready() -> None:
    if wait_for_server():
        webbrowser.open(URL)


def main() -> None:
    app_path = resource_path("app.py")
    app_dir = app_path.parent

    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    os.chdir(app_dir)

    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    bootstrap.run(
        str(app_path),
        "",
        [],
        flag_options={
            "server.headless": True,
            "server.port": PORT,
            "server.address": "localhost",
        },
    )


if __name__ == "__main__":
    main()
