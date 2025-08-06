import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# my modules
from kiosk_py.nfc_utils.reader import wait_for_card, read_reservation_from_card

def main():
    print("[TEST] Waiting for card...")
    try:
        tag_uid = wait_for_card()
        print(f"[TEST] Card detected: {tag_uid}")

        reservation = read_reservation_from_card()
        if reservation:
            print("[TEST] Reservation read from card:")
            for key, value in reservation.items():
                print(f"  {key}: {value}")
        else:
            print("[TEST] No reservation data found on card.")

    except Exception as e:
        print(f"[ERROR] Failed to read card: {e}")

if __name__ == "__main__":
    main()
