"""Single-command launcher: starts the local server and opens it in your browser."""

import threading
import time
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}/"


def _open_browser():
    time.sleep(1.5)
    try:
        webbrowser.open(URL)
    except Exception:
        pass  # the banner below still tells the user where to go


def _print_banner():
    line = "=" * 56
    print(f"\n{line}")
    print("  MMA UNIVERSE SIMULATOR is running.")
    print(f"\n  Open this in your browser:   {URL}")
    print("\n  (It should open automatically. If it didn't, copy the")
    print("   address above into your browser's address bar.)")
    print("\n  Leave this window open while you play.")
    print("  Press Ctrl+C here to stop the game.")
    print(f"{line}\n")


if __name__ == "__main__":
    _print_banner()
    threading.Thread(target=_open_browser, daemon=True).start()
    # log_level="warning" keeps the banner readable instead of burying it in request logs
    uvicorn.run("web.app:app", host=HOST, port=PORT, reload=False, log_level="warning")
