import time
import ndef
from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString

from kiosk_py.config import MOCK_NFC
from kiosk_py.ui import controller


def read_device_id(tag_uid):
    if MOCK_NFC:
        print("[TEST] Returning mock device ID")
        return "DEVICE-ID-12345"
    return tag_uid

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
        return uid, conn

    except Exception as e:
        print(f"[ERROR] Failed to detect card: {e}")
        return None, None


def write_reservation_to_card(reservation):
    try:
        print("[NFC] Please tap the card again to write reservation...")

        if MOCK_NFC:
            print("[MOCK] Skipping actual card write in mock mode.")
            return True

        controller.nfc_writing_in_progress = True
        print("[DEBUG] NFC polling paused for write operation.")

        # Fresh card connection
        cardtype = AnyCardType()
        cardrequest = CardRequest(timeout=10, cardType=cardtype)
        cardservice = cardrequest.waitforcard()
        conn = cardservice.connection
        conn.connect()

        # Optional: log UID
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = conn.transmit(GET_UID)
        if (sw1, sw2) == (0x90, 0x00):
            uid = ''.join(f'{b:02X}' for b in response)
            print(f"[NFC] Card connected. UID: {uid}")
        else:
            print("[WARNING] Failed to read UID.")

        # Prepare payload
        command_seq = 1
        attraction_id = reservation.get("attraction_id", 1)
        ride_name = reservation.get("ride_name", "")
        wait_time_secs = int(reservation.get("wait_time", 0) * 60)
        ride_name_bytes = ride_name.encode("ascii", errors="ignore")
        ride_name_len = len(ride_name_bytes)

        print("write stage 2")
        payload = bytearray(384)
        payload[0x40] = command_seq
        payload[0x43] = 0x40
        payload[0x44] = attraction_id & 0xFF
        payload[0x45] = ride_name_len & 0xFF
        payload[0x46:0x48] = wait_time_secs.to_bytes(2, byteorder='little')
        payload[0x80:0x80+ride_name_len] = ride_name_bytes

        print("write stage 3")
        record = ndef.Record('urn:nfc:ext:qb3:memory', '1', payload)
        msg = b''.join(ndef.message_encoder([record]))
        print("write stage 3.5")

        # Write to card
        conn.transmit([0x00, 0xA4, 0x04, 0x00, 0x07] + [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01])
        print("write stage 4")
        conn.transmit([0x00, 0xA4, 0x00, 0x0C, 0x02] + [0x00, 0x01])
        print("write stage 5")
        conn.transmit([0x00, 0xD6, 0x00, 0x00, 0x02, 0x00, 0x00])
        print("write stage 6")

        offset = 0
        total_len = len(msg)
        while offset < total_len:
            wr_len = min(0xF6, total_len - offset)
            print(f"[NFC] Write length {wr_len}")
            p1 = ((offset + 2) >> 8) & 0xFF
            p2 = (offset + 2) & 0xFF
            apdu = [0x00, 0xD6, p1, p2, wr_len] + list(msg[offset:offset+wr_len])
            conn.transmit(apdu)
            offset += wr_len

        print("write stage 7")
        length_bytes = [len(msg) >> 8, len(msg) & 0xFF]
        conn.transmit([0x00, 0xD6, 0x00, 0x00, 0x02] + length_bytes)

        print("[NFC] Reservation written successfully.")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to write reservation: {e}")
        return False

    finally:
        controller.nfc_writing_in_progress = False
        print("[DEBUG] NFC polling resumed.")

