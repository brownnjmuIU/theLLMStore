import subprocess
import sys
import time
import webbrowser
import urllib.request
from pathlib import Path

URL = "http://localhost:8501"
APP_PATH = str(Path(__file__).resolve().parent / "app.py")

def wait_for_server(url: str, timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except Exception:
            time.sleep(0.5)
    return False

def main() -> None:
    proc = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", APP_PATH,
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ])

    if wait_for_server(URL, timeout=30):
        webbrowser.open(URL)
    else:
        print("Streamlit did not start within 30 seconds.")

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()

if __name__ == "__main__":
    main()