import os
import sys
import threading
import webbrowser
from pathlib import Path

import streamlit.web.bootstrap as bootstrap

URL = "http://localhost:8501"


def resource_path(rel_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel_path


def main() -> None:
    app_path = resource_path("app.py")
    app_dir = app_path.parent

    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    os.chdir(app_dir)

    threading.Timer(2.0, lambda: webbrowser.open(URL)).start()
    bootstrap.run(
        str(app_path),
        "",
        [],
        flag_options={
            "server.headless": True,
            "server.port": 8501,
            "server.address": "localhost",
        },
    )


if __name__ == "__main__":
    main()
