from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest

def test_select_ndef():
    print("[INFO] Waiting for NFC card...")
    cardtype = AnyCardType()
    cardrequest = CardRequest(timeout=10, cardType=cardtype)
    cardservice = cardrequest.waitforcard()
    conn = cardservice.connection
    try:
        conn.connect()
    except Exception as e:
        print(f"[DEBUG] Could not reconnect: {e}")

    print("[INFO] Connected. Trying to select NDEF application...")
    try:
        resp, sw1, sw2 = conn.transmit([0x00, 0xA4, 0x04, 0x00, 0x07,
                                        0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01])
        print(f"[DEBUG] Select NDEF app: SW1={sw1:02X}, SW2={sw2:02X}, resp={resp}")
        resp, sw1, sw2 = conn.transmit([0x00, 0xA4, 0x00, 0x0C, 0x02, 0x00, 0x01])
        print(f"[DEBUG] Select NDEF file: SW1={sw1:02X}, SW2={sw2:02X}, resp={resp}")
    except Exception as e:
        print(f"[ERROR] Failed to select NDEF: {e}")

if __name__ == "__main__":
    test_select_ndef()