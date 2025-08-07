import os
import requests
from flask import redirect, url_for
import webview
import threading

#my modules
from kiosk_py.services import api_client
from kiosk_py.nfc_utils import reader, writer
from kiosk_py.utils.timer import reset_timer
from kiosk_py.config import MOCK_NFC, MOCK_API
from kiosk_py.nfc_utils.reader import start_card_polling

# Global state
selected_attraction = None
device_id = None
last_tag = None
existing_reservation = None
nfc_writing_in_progress = False

import threading

def safe_evaluate_js(js_code):
    def run_js():
        try:
            if webview.windows:
                webview.windows[0].evaluate_js(js_code)
            else:
                print("[WARNING] No webview window available to evaluate JS.")
        except Exception as e:
            print(f"[ERROR] Failed to evaluate JS: {e}")

    threading.Thread(target=run_js).start()


def handle_card_poll(tag_uid, reservation, guest_email):
    global last_tag, device_id, existing_reservation, nfc_writing_in_progress

    if nfc_writing_in_progress:
        print("[DEBUG] Skipping card poll during write operation.")
        return

    if tag_uid == last_tag:
        return  # Prevent repeated triggers
    last_tag = tag_uid

    print(f"[NFC] Card tapped with UID: {tag_uid}")
    print(f"[NFC] Reservation data: {reservation}")
    print(f"[NFC] Guest email from card: {guest_email}")

    safe_evaluate_js("""
      const spinner = document.getElementById('spinner');
      if (spinner) spinner.style.display = 'flex';
    """)

    try:
        if MOCK_API:
            print("[MOCK] Skipping login in mock API mode")
            device_id = "MOCK-DEVICE-ID"
        else:
            if not guest_email:
                print("[ERROR] No guest email found on card.")
                return
            email = guest_email
            password = tag_uid
            device_id = api_client.login(email, password)
            print(f"[LOGIN] Logged in as {email}, device ID: {device_id}")

        if reservation and reservation.get("ride_name"):
            existing_reservation = reservation
            print("[DEBUG] Existing reservation found. Redirecting to /replace_prompt")
            safe_evaluate_js("window.location.href = '/replace_prompt'")
        else:
            load_attractions_and_render()
            print("[DEBUG] No reservation found. Redirecting to /select")
            safe_evaluate_js("window.location.href = '/select'")

    except Exception as e:
        print(f"[ERROR] Login failed: {e}")


# Start polling when controller is loaded
start_card_polling(handle_card_poll)

def handle_card_tap():
    if MOCK_NFC:
        print("[TEST] Using mock device ID")
        return "TEST-DEVICE-001"
    else:
        tag = reader.wait_for_card()
        return reader.read_device_id(tag)

def display_welcome_screen():
    print("[UI] Showing welcome screen")

def load_attractions_and_render():
    attractions = api_client.fetch_attractions() #device_id?
    print("[API] Attractions fetched:", attractions)

    # Assign attraction_id based on alphabetical order of ride_name
    sorted_attractions = sorted(attractions, key=lambda x: x.get("name", "").lower())
    for idx, attraction in enumerate(sorted_attractions):
        attraction["attraction_id"] = idx

    return sorted_attractions

def download_and_cache_images(attractions, static_folder='static/images'):
    if not os.path.exists(static_folder):
        os.makedirs(static_folder)

    for attraction in attractions:
        ride_id = attraction.get('id')
        image_url = attraction.get('image')

        if not ride_id or not image_url:
            continue

        file_path = os.path.join(static_folder, f"{ride_id}.jpg")

        if os.path.exists(file_path):
            print(f"[CACHE] Image already exists for {ride_id}, skipping download.")
            continue

        try:
            print(f"[DOWNLOAD] Fetching image for {ride_id} from {image_url}")
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
            }
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                f.write(response.content)

            print(f"[SUCCESS] Image saved to {file_path}")

        except Exception as e:
            print(f"[ERROR] Failed to download image for {ride_id}: {e}")

def handle_selection(attraction_id):
    global selected_attraction
    selected_attraction = api_client.make_reservation(device_id, attraction_id)
    print("[API] Reservation successful:", selected_attraction)

def make_reservation(ride_id, guest_count=1):
    try:
        attraction = api_client.fetch_attraction_details(ride_id)
        ride_name = attraction.get("data", {}).get("name", "Unknown Ride")
        wait_time = attraction.get("data", {}).get("wait_time_mins", 0)

        raw = api_client.make_reservation(device_id, ride_id, guest_count)

        reservation = {
            "ride_id": ride_id,
            "ride_name": ride_name,
            "wait_time": wait_time,
            "confirmation_id": raw.get("id", "UNKNOWN")
        }

        print(f"[API] Reservation successful: {raw}")
        return reservation

    except Exception as e:
        print(f"[ERROR] Failed to make reservation: {e}")
        raise

def confirm_and_write_to_card(ride):
    global nfc_writing_in_progress

    reservation = api_client.make_reservation(ride["id"])

    if MOCK_API:
        print(f"[TEST] Reservation confirmed: {reservation}")
    else:
        nfc_writing_in_progress = True
        success = writer.write_reservation_to_card(reservation)
        nfc_writing_in_progress = False
        if not success:
            print("[ERROR] Failed to write reservation to card.")

    return reservation

def display_success_then_reset():
    print("[UI] Showing success screen")
    reset_timer(seconds=4)
