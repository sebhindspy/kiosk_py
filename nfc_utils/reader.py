import time
import threading
import traceback
from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString
import ndef

from kiosk_py.config import MOCK_NFC
from kiosk_py.ui import controller

def read_device_id(tag_uid):
    if MOCK_NFC:
        print("[TEST] Returning mock device ID")
        return "DEVICE-ID-12345"
    return tag_uid

def read_guest_email_from_card(conn):
    """
    Reads guest email from card using:
    - email_length at 0x100 (1 byte)
    - guest_email at 0x101 (max 127 bytes)
    Returns the email as a string, or None if not found/invalid.
    """
    try:
        # Read email_length
        apdu = [0x00, 0xB0, 0x01, 0x14, 0x01]  # 0x114 offset
        response, sw1, sw2 = conn.transmit(apdu)
        if (sw1, sw2) != (0x90, 0x00) or not response:
            print("[DEBUG] Failed to read email length from card")
            return None
        email_length = response[0]
        if email_length == 0 or email_length > 127:
            print(f"[DEBUG] Invalid email length: {email_length}")
            return None

        # Read guest_email
        apdu = [0x00, 0xB0, 0x01, 0x15, email_length]  # 0x115 offset
        response, sw1, sw2 = conn.transmit(apdu)
        if (sw1, sw2) != (0x90, 0x00) or not response:
            print("[DEBUG] Failed to read guest email from card")
            return None
        guest_email = bytes(response).decode('utf-8', errors='ignore')
        print(f"[DEBUG] Guest email read from card: {guest_email}")
        return guest_email
    except Exception as e:
        print(f"[ERROR] Exception reading guest email: {e}")
        return None


def wait_for_card(timeout=10):
    if MOCK_NFC:
        print("[TEST] Simulating card tap...")
        time.sleep(1)
        return "MOCK_TAG", None

    try:
        cardtype = AnyCardType()
        cardrequest = CardRequest(timeout=timeout, cardType=cardtype)
        cardservice = cardrequest.waitforcard()
        conn = cardservice.connection
        conn.connect()

        # Get UID
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = conn.transmit(GET_UID)
        if (sw1, sw2) != (0x90, 0x00):
            raise RuntimeError("Failed to get UID")
        uid = ''.join(f'{b:02X}' for b in response)

        print(f"[NFC] Card connected. UID: {uid}")
        return uid, cardservice

    except Exception as e:
        print(f"[ERROR] Failed to detect card: {e}")
        return None, None

def read_reservation_from_card(conn):
    try:
        # Attempt to reconnect safely
        try:
            conn.connect()
            print("[DEBUG] Reconnected to card.")
        except Exception as reconnect_error:
            print(f"[DEBUG] Reconnect skipped or failed: {reconnect_error}")
        
        time.sleep(0.1)  # Small delay to stabilize connection

        print("[DEBUG] Selecting NDEF application...")
        conn.transmit([0x00, 0xA4, 0x04, 0x00, 0x07] + [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01])

        print("[DEBUG] Selecting NDEF file...")
        conn.transmit([0x00, 0xA4, 0x00, 0x0C, 0x02] + [0x00, 0x01])

        print("[DEBUG] Reading NDEF length...")
        apdu = [0x00, 0xB0, 0x00, 0x00, 0x02]
        response, sw1, sw2 = conn.transmit(apdu)
        print(f"[DEBUG] Raw NDEF length response: {response}, SW1: {sw1}, SW2: {sw2}")
        if (sw1, sw2) != (0x90, 0x00):
            raise RuntimeError("Failed to read NDEF length")
        ndef_length = (response[0] << 8) + response[1]
        print(f"[DEBUG] NDEF length: {ndef_length}")

        message = []
        offset = 0
        while offset < ndef_length:
            read_len = min(0xF6, ndef_length - offset)
            p1 = ((offset + 2) >> 8) & 0xFF
            p2 = (offset + 2) & 0xFF
            apdu = [0x00, 0xB0, p1, p2, read_len]
            chunk, sw1, sw2 = conn.transmit(apdu)
            if (sw1, sw2) != (0x90, 0x00):
                raise RuntimeError("Failed to read NDEF message chunk")
            message += chunk
            offset += read_len

        print("[DEBUG] Decoding NDEF message...")
        octets = bytearray(message)
        for record in ndef.message_decoder(octets):
            print(f"[DEBUG] NDEF record type: {record.type}")
            print(f"[DEBUG] NDEF payload (hex): {record.data.hex()}")

            if record.type == 'urn:nfc:ext:qb3:memory':
                payload = bytearray(record.data)

                # Check for placeholder or invalid data
                if all(b == 0xAA for b in payload):
                    print("[DEBUG] Payload is all 0xAA — likely uninitialized or test card.")
                    return None

                if len(payload) < 0x48:
                    print("[DEBUG] Payload too short to contain valid reservation.")
                    return None

                try:
                    attraction_id = payload[0x44]
                    ride_name_len = payload[0x45]
                    wait_time_secs = int.from_bytes(payload[0x46:0x48], byteorder='big')

                    if len(payload) < 0x80 + ride_name_len:
                        print("[DEBUG] Payload too short for ride name.")
                        return None

                    ride_name = payload[0x80:0x80+ride_name_len].decode("ascii", errors="ignore")

                    return {
                        "wait_time": int(wait_time_secs/60),
                        "ride_name": ride_name,
                        "attraction_id": attraction_id
                    }
                
                except Exception as decode_error:
                    print(f"[DEBUG] Failed to decode reservation fields: {decode_error}")
                    return None

            return None


    except Exception as e:
        print(f"[ERROR] Failed to read reservation: {e}")
        traceback.print_exc()
        return None


def start_card_polling(callback, poll_interval=2):
    def poll_loop():
        print("[NFC] Starting card polling loop...")
        while True:
            if controller.nfc_writing_in_progress == False:
                time.sleep(poll_interval)
                try:
                    if MOCK_NFC:
                        time.sleep(2)
                        tag_uid = "MOCK_TAG"
                        reservation = {
                            "wait_time": 300,
                            "ride_name": "MOCK_RIDE",
                            "attraction_id": 1
                        }
                        guest_email = "mock@example.com"
                        print("[MOCK] Simulating card tap")
                        callback(tag_uid, reservation, guest_email)
                        time.sleep(poll_interval)
                        continue

                    tag_uid, cardservice = wait_for_card()
                    if not tag_uid or not cardservice:
                        time.sleep(poll_interval)
                        continue

                    reservation = read_reservation_from_card(cardservice.connection)
                    guest_email = read_guest_email_from_card(cardservice.connection)
                    if tag_uid:
                        try:
                            callback(tag_uid, reservation, guest_email)
                        except Exception as e:
                            print(f"[READER ERROR] Exception in callback: {e}")
                            traceback.print_exc()
                    else:
                        print("[NFC] No UID found.")

                except Exception as e:
                    print(f"[NFC] Polling error: {e}")
                    traceback.print_exc()

            else:
                print("[DEBUG]Polling paused while writing")      
            
            time.sleep(poll_interval)

    thread = threading.Thread(target=poll_loop, daemon=True)
    thread.start()
