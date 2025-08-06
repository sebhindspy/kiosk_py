import time
import threading
import nfc
import ndef  # Correct import from ndeflib

from config import MOCK_NFC

def read_device_id(tag_uid):
    """
    Returns a device ID based on the tag UID.
    """
    if MOCK_NFC:
        print("[TEST] Returning mock device ID")
        return "DEVICE-ID-12345"
    return tag_uid

def parse_qb3_memory_record(tag):
    """
    Parses the qb3:memory NDEF record from the tag and returns the reservation data.
    """
    if not tag.ndef:
        print("[ERROR] Tag is not NDEF formatted.")
        return None

    try:
        for record in ndef.message_decoder(tag.ndef.message):
            if record.type == "urn:nfc:ext:qb3:memory":
                payload = bytearray(record.data)

                command_seq = payload[0]
                command_flag = payload[1]
                attraction_id = payload[2]
                ride_name_len = payload[3]
                wait_time_secs = int.from_bytes(payload[4:6], byteorder='big')
                ride_name = payload[6:6+ride_name_len].decode("ascii", errors="ignore")

                return {
                    "command_seq": command_seq,
                    "command_flag": command_flag,
                    "attraction_id": attraction_id,
                    "wait_time": wait_time_secs,
                    "ride_name": ride_name
                }

        print("[ERROR] No qb3:memory record found.")
        return None

    except Exception as e:
        print(f"[ERROR] Failed to parse NDEF record: {e}")
        return None

def wait_for_card(timeout=10):
    """
    Waits for a card and returns its UID or 'MOCK_TAG' in mock mode.
    """
    if MOCK_NFC:
        print("[TEST] Simulating card tap...")
        time.sleep(1)
        return "MOCK_TAG"

    try:
        with nfc.ContactlessFrontend('usb') as clf:
            print("[NFC] Waiting for tag...")
            tag = clf.connect(rdwr={'on-connect': lambda tag: False}, terminate=lambda: False, timeout=timeout)
            if tag:
                return tag.identifier.hex().upper()
    except Exception as e:
        raise RuntimeError(f"[ERROR] NFC reader error: {e}")

    raise RuntimeError("No card detected within timeout.")

def start_card_polling(callback):
    """
    Starts a background thread that polls for card taps and calls `callback(tag_uid, reservation_data)` when detected.
    """
    def poll_loop():
        print("[NFC] Starting card polling loop...")
        while True:
            try:
                if MOCK_NFC:
                    tag_uid = "MOCK_TAG"
                    reservation = {
                        "command_seq": 1,
                        "command_flag": 0x40,
                        "attraction_id": 1,
                        "wait_time": 1800,
                        "ride_name": "TEST_RIDE"
                    }
                    callback(tag_uid, reservation)
                    time.sleep(2)
                    continue

                with nfc.ContactlessFrontend('usb') as clf:
                    tag = clf.connect(rdwr={'on-connect': lambda tag: True})
                    tag_uid = tag.identifier.hex().upper()
                    print(f"[NFC] Card detected: {tag_uid}")
                    reservation = parse_qb3_memory_record(tag)
                    if reservation:
                        callback(tag_uid, reservation)
                    time.sleep(2)

            except Exception as e:
                print(f"[NFC] Polling error: {e}")
                time.sleep(1)

    thread = threading.Thread(target=poll_loop, daemon=True)
    thread.start()
