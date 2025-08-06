# utils/timer.py
import threading
import webview

_timer = None

def reset_timer(seconds=10):
    global _timer
    if _timer:
        _timer.cancel()
    _timer = threading.Timer(seconds, go_to_welcome)
    _timer.start()

def go_to_welcome():
    print("[UI] Timeout reached. Returning to welcome screen.")
    webview.windows[0].load_url("http://localhost:5000/")