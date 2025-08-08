import time
import ndef
from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString

def write_data_to_card():
    try:
        print("[NFC] Please tap the card again to write reservation and email...")

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

        # Prepare reservation payload
        command_seq = 1
        attraction_id = 99
        ride_name = "blank_ride"
        wait_time_secs = 5940
        ride_name_bytes = ride_name.encode("ascii", errors="ignore")
        ride_name_len = len(ride_name_bytes)
        user_email = "cat@dog.com"
        user_email_bytes = user_email.encode("ascii", errors="ignore")
        user_email_len = len(user_email_bytes)

        # Reservation payload (384 bytes)
        payload = bytearray(384)
        payload[0x40] = command_seq
        payload[0x43] = 0x40
        payload[0x44] = attraction_id & 0xFF
        payload[0x45] = ride_name_len & 0xFF
        payload[0x46:0x48] = wait_time_secs.to_bytes(2, byteorder='little')
        payload[0x80:0x80+ride_name_len] = ride_name_bytes

        record = ndef.Record('urn:nfc:ext:qb3:memory', '1', payload)
        msg = b''.join(ndef.message_encoder([record]))

        # Write reservation NDEF
        conn.transmit([0x00, 0xA4, 0x04, 0x00, 0x07] + [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01])
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

        # Write email length and email directly to 0x100/0x101
        print(f"[NFC] Writing email length ({user_email_len}) to 0x100...")
        conn.transmit([0x00, 0xD6, 0x01, 0x00, 0x01, user_email_len])

        print(f"[NFC] Writing email '{user_email}' to 0x101...")
        conn.transmit([0x00, 0xD6, 0x01, 0x01, user_email_len] + list(user_email_bytes))
        print("[NFC] Email data written successfully.")

        length_bytes = [len(msg) >> 8, len(msg) & 0xFF]
        conn.transmit([0x00, 0xD6, 0x00, 0x00, 0x02] + length_bytes)
        print("[NFC] Reservation data written.")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to write data: {e}")
        return False

if __name__ == "__main__":
    write_data_to_card()
    print("[INFO] Please tap the card to write")
    time.sleep(2)