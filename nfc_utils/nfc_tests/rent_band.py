import time
import ndef
from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.Exceptions import CardConnectionException

EMAIL = "cat@dog.com"
EMAIL_BYTES = EMAIL.encode("ascii")
EMAIL_LEN = len(EMAIL_BYTES)

def wait_for_card(timeout=10):
    print("[INFO] Waiting for NFC card...")
    cardtype = AnyCardType()
    cardrequest = CardRequest(timeout=timeout, cardType=cardtype)
    cardservice = cardrequest.waitforcard()
    conn = cardservice.connection
    conn.connect()

    try:
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = conn.transmit(GET_UID)
        if (sw1, sw2) == (0x90, 0x00):
            uid = ''.join(f'{b:02X}' for b in response)
            print(f"[INFO] Card connected. UID: {uid}")
    except Exception as e:
        print(f"[WARNING] Could not read UID: {e}")

    return conn

"""def write_blank_reservation():
    try:
        conn = wait_for_card()
        print("[INFO] Writing blank reservation to card...")

        # Ensure connection is active
        try:
            conn.connect()
        except Exception:
            pass  # Already connected or cannot reconnect


        payload = bytearray([0xAA] * 384)
        record = ndef.Record('urn:nfc:ext:qb3:memory', '1', payload)
        msg = b''.join(ndef.message_encoder([record]))

        conn.transmit([0x00, 0xA4, 0x04, 0x00, 0x07] +
                      [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01])
        conn.transmit([0x00, 0xA4, 0x00, 0x0C, 0x02] + [0x00, 0x01])
        conn.transmit([0x00, 0xD6, 0x00, 0x00, 0x02, 0x00, 0x00])

        offset = 0
        total_len = len(msg)
        while offset < total_len:
            wr_len = min(0xF6, total_len - offset)
            p1 = ((offset + 2) >> 8) & 0xFF
            p2 = (offset + 2) & 0xFF
            apdu = [0x00, 0xD6, p1, p2, wr_len] + list(msg[offset:offset+wr_len])
            conn.transmit(apdu)
            offset += wr_len

        length_bytes = [len(msg) >> 8, len(msg) & 0xFF]
        conn.transmit([0x00, 0xD6, 0x00, 0x00, 0x02] + length_bytes)

        print("[SUCCESS] Blank reservation written.")
    except CardConnectionException as e:
        print(f"[ERROR] Failed to write blank reservation: {e}")

def write_email_to_card():
    try:
        conn = wait_for_card()
        print(f"[INFO] Writing email length ({EMAIL_LEN}) to offset 0x100...")

        # Ensure connection is active
        try:
            conn.connect()
        except Exception:
            pass  # Already connected or cannot reconnect

        # Select NDEF application and file (critical!)
        conn.transmit([0x00, 0xA4, 0x04, 0x00, 0x07] +
                      [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01])
        conn.transmit([0x00, 0xA4, 0x00, 0x0C, 0x02] + [0x00, 0x01])

        # Write email length to 0x100
        print(f"[INFO] Writing email length ({EMAIL_LEN}) to offset 0x100...")
        conn.transmit([0x00, 0xD6, 0x01, 0x00, 0x01, EMAIL_LEN])

        print(f"[INFO] Writing email '{EMAIL}' to offset 0x101...")
        # Write guest_email to 0x101
        offset = 0
        total_len = len(EMAIL_BYTES)
        while offset < total_len:
            wr_len = min(0xF6, total_len - offset)
            p1 = ((0x101 + offset) >> 8) & 0xFF
            p2 = (0x101 + offset) & 0xFF
            apdu = [0x00, 0xD6, p1, p2, wr_len] + list(EMAIL_BYTES[offset:offset+wr_len])
            conn.transmit(apdu)
            offset += wr_len

        print("[SUCCESS] Email written to card.")
    except CardConnectionException as e:
        print(f"[ERROR] Failed to write email: {e}")

if __name__ == "__main__":
    write_blank_reservation()
    print("[INFO] Please tap the card again to write the email...")
    time.sleep(2)
    write_email_to_card()"""

def write_blank_and_email():
    try:
        conn = wait_for_card()
        try:
            conn.connect()
        except Exception:
            pass

        # Select NDEF application and file
        conn.transmit([0x00, 0xA4, 0x04, 0x00, 0x07] +
                      [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01])
        conn.transmit([0x00, 0xA4, 0x00, 0x0C, 0x02] + [0x00, 0x01])

        # Write blank reservation
        print("[INFO] Writing blank reservation to card...")
        payload = bytearray([0xAA] * 384)
        record = ndef.Record('urn:nfc:ext:qb3:memory', '1', payload)
        msg = b''.join(ndef.message_encoder([record]))

        conn.transmit([0x00, 0xD6, 0x00, 0x00, 0x02, 0x00, 0x00])

        offset = 0
        total_len = len(msg)
        while offset < total_len:
            wr_len = min(0xF6, total_len - offset)
            p1 = ((offset + 2) >> 8) & 0xFF
            p2 = (offset + 2) & 0xFF
            apdu = [0x00, 0xD6, p1, p2, wr_len] + list(msg[offset:offset+wr_len])
            conn.transmit(apdu)
            offset += wr_len

        length_bytes = [len(msg) >> 8, len(msg) & 0xFF]
        conn.transmit([0x00, 0xD6, 0x00, 0x00, 0x02] + length_bytes)
        print("[SUCCESS] Blank reservation written.")

        # Write email length and email
        print(f"[INFO] Writing email length ({EMAIL_LEN}) to offset 0x100...")
        conn.transmit([0x00, 0xD6, 0x01, 0x00, 0x01, EMAIL_LEN])

        print(f"[INFO] Writing email '{EMAIL}' to offset 0x101...")
        offset = 0
        total_len = len(EMAIL_BYTES)
        while offset < total_len:
            wr_len = min(0xF6, total_len - offset)
            p1 = ((0x101 + offset) >> 8) & 0xFF
            p2 = (0x101 + offset) & 0xFF
            apdu = [0x00, 0xD6, p1, p2, wr_len] + list(EMAIL_BYTES[offset:offset+wr_len])
            conn.transmit(apdu)
            offset += wr_len

        print("[SUCCESS] Email written to card.")

    except CardConnectionException as e:
        print(f"[ERROR] Failed to write to card: {e}")

if __name__ == "__main__":
    write_blank_and_email()