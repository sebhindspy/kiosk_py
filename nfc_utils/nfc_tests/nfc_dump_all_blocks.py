# nfc_dump_all_blocks.py

from smartcard.System import readers
from smartcard.Exceptions import CardConnectionException, NoCardException

DEFAULT_KEY = [0xFF] * 6
BLOCK_RANGE = range(0, 64)  # MIFARE Classic 1K has 64 blocks (0–63)

def read_block(connection, block_num):
    # Authenticate
    auth_apdu = [0xFF, 0x86, 0x00, 0x00, 0x05,
                 0x01, 0x00, block_num, 0x60, 0x00]
    connection.transmit(auth_apdu)

    # Read 4 bytes per block
    read_apdu = [0xFF, 0xB0, 0x00, block_num, 0x04]
    data, sw1, sw2 = connection.transmit(read_apdu)

    if (sw1, sw2) != (0x90, 0x00):
        raise RuntimeError(f"Read failed at block {block_num}: {hex(sw1)} {hex(sw2)}")
    return data

def main():
    try:
        r = readers()
        reader = next((rd for rd in r if "FEIG" in str(rd) and "Slot:CL" in str(rd)), None)
        if not reader:
            raise RuntimeError("FEIG reader not found.")

        connection = reader.createConnection()
        connection.connect()

        print("[DUMP] Reading all blocks (4 bytes each)...")
        for block in BLOCK_RANGE:
            try:
                data = read_block(connection, block)
                hex_data = ' '.join(f'{b:02X}' for b in data)
                print(f"Block {block:02}: {hex_data}")
            except Exception as e:
                print(f"Block {block:02}: [ERROR] {e}")

    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
