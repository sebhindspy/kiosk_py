from smartcard.System import readers
from smartcard.Exceptions import NoCardException, CardConnectionException

DEFAULT_KEY = [0xFF] * 6
BLOCK_META = 4
BLOCK_NAME_START = 8
MAX_BLOCKS = 2  # Supports up to 64 bytes of ride name

def write_reservation_to_card(tag_uid, reservation):
    """
    Writes a reservation to a MIFARE Classic EV1 1K card using APDU commands.
    Metadata is written to block 4, and ride name is written starting at block 32.
    """

    try:
        r = readers()
        if not r:
            raise RuntimeError("No PC/SC readers found.")

        feig_reader = next((reader for reader in r if "FEIG" in str(reader) and "Slot:CL" in str(reader)), None)
        if not feig_reader:
            raise RuntimeError("FEIG reader not found.")

        connection = feig_reader.createConnection()
        connection.connect()

        # Extract and encode fields
        ride_name = reservation["ride_name"]
        ride_name_bytes = ride_name.encode("ascii", errors="ignore")
        ride_name_len = len(ride_name_bytes)
        wait_time = int(reservation["wait_time"])  # already in minutes
        attraction_id = int(reservation.get("attraction_id", 1))

        # --- Write metadata block (block 4) ---
        meta_payload = bytearray()
        meta_payload.append(wait_time)           # 1 byte
        meta_payload.append(ride_name_len)       # 1 byte
        meta_payload.append(attraction_id)       # 1 byte
        meta_payload += bytes([0x00] * (16 - len(meta_payload)))  # pad to 16 bytes

        # Authenticate and write metadata
        auth_apdu = [0xFF, 0x86, 0x00, 0x00, 0x05,
                     0x01, 0x00, BLOCK_META, 0x60, 0x00]
        connection.transmit(auth_apdu)

        write_apdu = [0xFF, 0xD6, 0x00, BLOCK_META, 0x10] + list(meta_payload)
        response, sw1, sw2 = connection.transmit(write_apdu)
        if (sw1, sw2) != (0x90, 0x00):
            raise RuntimeError(f"Write failed at block {BLOCK_META}: {hex(sw1)} {hex(sw2)}")

        # --- Write ride name across multiple blocks ---
        padded_name = ride_name_bytes + bytes([0x00] * (16 * MAX_BLOCKS - len(ride_name_bytes)))
        for i in range(MAX_BLOCKS):
            block_num = BLOCK_NAME_START + i
            chunk = padded_name[i*16:(i+1)*16]

            # Authenticate
            auth_apdu = [0xFF, 0x86, 0x00, 0x00, 0x05,
                         0x01, 0x00, block_num, 0x60, 0x00]
            connection.transmit(auth_apdu)

            # Write block
            write_apdu = [0xFF, 0xD6, 0x00, block_num, 0x10] + list(chunk)
            response, sw1, sw2 = connection.transmit(write_apdu)
            if (sw1, sw2) != (0x90, 0x00):
                raise RuntimeError(f"Write failed at block {block_num}: {hex(sw1)} {hex(sw2)}")
        
        print(f"[DEBUG] Writing to block {block_num}: {chunk}")
        print("[NFC] Reservation written successfully.")

    except NoCardException:
        print("[ERROR] No card detected. Please place a card on the reader.")
    except CardConnectionException as e:
        print(f"[ERROR] Card connection failed: {e}")
    except Exception as e:
        print(f"[ERROR] Failed to write to card: {e}")
