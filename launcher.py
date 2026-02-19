import os
import sys
import time
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
    app_dir = app_path.parent

    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    os.chdir(app_dir)

    # Point Streamlit to the bundled config file
    # Using "streamlit_config" instead of ".streamlit" as PyInstaller
    # silently skips dot-folders on Windows
    config_dir = resource_path("streamlit_config")
    os.environ["STREAMLIT_CONFIG_DIR"] = str(config_dir)

    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    from streamlit.web import bootstrap
    bootstrap.run(
        str(app_path),
        False,
        [],
        flag_options={},
    )


if __name__ == "__main__":
    main()