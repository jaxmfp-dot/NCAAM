"""Single-command launcher: starts the local server and opens it in your browser."""

import threading
import time
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000


def _open_browser():
    time.sleep(1.0)
    webbrowser.open(f"http://{HOST}:{PORT}/")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("web.app:app", host=HOST, port=PORT, reload=False)
