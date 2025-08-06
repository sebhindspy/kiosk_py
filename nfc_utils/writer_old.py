import nfc
import ndef  # Correct import from ndeflib

def write_reservation_to_card(reservation):
    """
    Writes a reservation to an NTAG card using an NDEF External Type Record.
    The record has domain:type = qb3:memory and includes:
    - Command sequence (1 byte)
    - Command flag (1 byte)
    - Attraction ID (1 byte)
    - Ride name length (1 byte)
    - Wait time in seconds (2 bytes)
    - Ride name in ASCII (up to 32 bytes)
    """

    def on_connect(tag):
        if not tag.ndef:
            print("[ERROR] Tag is not NDEF formatted.")
            return False
        try:
            # Extract and encode fields
            ride_name = reservation["ride_name"]
            ride_name_bytes = ride_name.encode("ascii", errors="ignore")[:32]
            ride_name_len = len(ride_name_bytes)
            wait_time_secs = int(reservation["wait_time"]) * 60
            attraction_id = int(reservation.get("attraction_id", 1))

            # Construct binary payload
            payload = bytearray()
            payload.append(1)  # Command sequence
            payload.append(0x40)  # Command flag
            payload.append(attraction_id)  # Attraction ID
            payload.append(ride_name_len)  # Ride name length
            payload += wait_time_secs.to_bytes(2, byteorder='big')  # Wait time
            payload += ride_name_bytes  # Ride name

            # Create NDEF External Type Record using ndeflib
            record = ndef.Record("urn:nfc:ext:qb3:memory", data=bytes(payload))
            message = ndef.Message(record)

            # Write to tag
            tag.ndef.message = message
            print("[NFC] NDEF record written successfully.")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to encode or write NDEF record: {e}")
            return False

    try:
        with nfc.ContactlessFrontend('usb') as clf:
            print("[NFC] Waiting for tag...")
            clf.connect(rdwr={'on-connect': on_connect})
    except IOError:
        print("[ERROR] NFC reader not found or not connected.")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
