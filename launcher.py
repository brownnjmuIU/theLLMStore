import subprocess
import sys
import time
import webbrowser
import urllib.request
from pathlib import Path

PORT = 8501
URL = f"http://127.0.0.1:{PORT}"

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

def main():
    app_path = resource_path("app.py")

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port=8501",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--server.baseUrlPath="
    ]

    proc = subprocess.Popen(cmd)

    # Wait for server ONCE
    if wait_for_server():
        webbrowser.open(URL)

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()

if __name__ == "__main__":
    main()