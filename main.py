
from kiosk_py.services import api_client
from kiosk_py.utils import timer

from kiosk_py.ui.screens import app
print("Imported app...")
import webview
import threading
import time
import socket

def wait_for_server(host="127.0.0.1", port=5000, timeout=10):
    start = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                print("Flask is up!")
                return
        except (OSError, ConnectionRefusedError):
            if time.time() - start > timeout:
                raise RuntimeError("Server did not become available in time.")
            time.sleep(0.2)

def start_flask():
    try:
        print("Starting Flask app...")
        app.run(debug=True, use_reloader=False, host="127.0.0.1", port=5000)
    except Exception as e:
        print(f"Flask failed to start: {e}")

class ApiBridge:
    def __init__(self):
        self.attraction_selected = None

    def select_attraction(self, attraction_id):
        self.attraction_selected = attraction_id
        # Optional: trigger reservation flow from here

if __name__ == "__main__":
    # Start Flask in a thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    print("flask thread started")

    #wait for flask to be ready

    wait_for_server()
    print("waited for server")

    # Launch the kiosk UI once flask is listening

    bridge = ApiBridge()

    webview.create_window("Ride Kiosk", "http://127.0.0.1:5000", fullscreen=True, js_api=bridge)
    print("window created")
    webview.start(debug=True)

