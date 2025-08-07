from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest

EMAIL = "cat@dog.com"
EMAIL_BYTES = EMAIL.encode("ascii")
EMAIL_LEN = len(EMAIL_BYTES)

def write_and_read_email():
    print("[INFO] Waiting for NFC card...")
    cardtype = AnyCardType()
    cardrequest = CardRequest(timeout=10, cardType=cardtype)
    cardservice = cardrequest.waitforcard()
    conn = cardservice.connection
    conn.connect()

    # Select NDEF application and file
    conn.transmit([0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01])
    conn.transmit([0x00, 0xA4, 0x00, 0x0C, 0x02, 0x00, 0x01])

    # Write email length to 0x100
    print(f"[INFO] Writing email length ({EMAIL_LEN}) to 0x100...")
    conn.transmit([0x00, 0xD6, 0x01, 0x00, 0x01, EMAIL_LEN])

    # Write email to 0x101
    print(f"[INFO] Writing email '{EMAIL}' to 0x101...")
    conn.transmit([0x00, 0xD6, 0x01, 0x01, EMAIL_LEN] + list(EMAIL_BYTES))

    # Read back email length
    resp, sw1, sw2 = conn.transmit([0x00, 0xB0, 0x01, 0x00, 0x01])
    print(f"[DEBUG] Read email length: {resp}, SW1={sw1:02X}, SW2={sw2:02X}")

    # Read back email
    resp, sw1, sw2 = conn.transmit([0x00, 0xB0, 0x01, 0x01, EMAIL_LEN])
    print(f"[DEBUG] Read email: {bytes(resp).decode('ascii')}, SW1={sw1:02X}, SW2={sw2:02X}")

if __name__ == "__main__":
    write_and_read_email()