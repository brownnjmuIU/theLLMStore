import os
import sys
import time
import subprocess
import threading
import webbrowser
import urllib.request
from pathlib import Path

PORT = 8501
URL = f"http://127.0.0.1:{PORT}"

opened = False


def resource_path(rel_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return base / rel_path


def wait_for_server(timeout: int = 60) -> bool:
    health_url = f"{URL}/_stcore/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def open_browser_when_ready() -> None:
    global opened
    if opened:
        return
    if wait_for_server(timeout=60):
        opened = True
        webbrowser.open(URL)
    else:
        print(f"Server did not become ready at {URL} within timeout.")


def main() -> None:
    app_path = resource_path("app.py")

    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m", "streamlit",
            "run", str(app_path),
            "--server.headless=true",
            f"--server.port={PORT}",
            "--server.address=127.0.0.1",
            "--server.fileWatcherType=none",
        ],
        cwd=str(app_path.parent),
    )
    proc.wait()


if __name__ == "__main__":
    main()