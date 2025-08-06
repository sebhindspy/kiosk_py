import time
import threading
import traceback
from smartcard.System import readers
from smartcard.Exceptions import NoCardException, CardConnectionException

from kiosk_py.config import MOCK_NFC

DEFAULT_KEY = [0xFF] * 6
BLOCK_TO_READ = 4  # Change this to the block where your data is stored

def read_device_id(tag_uid):
    if MOCK_NFC:
        print("[TEST] Returning mock device ID")
        return "DEVICE-ID-12345"
    return tag_uid

def parse_qb3_memory_block(data):
    try:
        command_seq = data[0]
        command_flag = data[1]
        attraction_id = data[2]
        ride_name_len = data[3]
        wait_time_secs = int.from_bytes(data[4:6], byteorder='big')
        ride_name = bytes(data[6:6+ride_name_len]).decode("ascii", errors="ignore")

        return {
            "command_seq": command_seq,
            "command_flag": command_flag,
            "attraction_id": attraction_id,
            "wait_time": wait_time_secs,
            "ride_name": ride_name
        }
    except Exception as e:
        print(f"[ERROR] Failed to parse memory block: {e}")
        return None

def wait_for_card(timeout=10):
    if MOCK_NFC:
        print("[TEST] Simulating card tap...")
        time.sleep(1)
        return "MOCK_TAG"

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = readers()
            if not r:
                raise RuntimeError("No PC/SC readers found.")

            feig_reader = next((reader for reader in r if "FEIG" in str(reader) and "Slot:CL" in str(reader)), None)
            if not feig_reader:
                raise RuntimeError("FEIG reader not found.")

            connection = feig_reader.createConnection()  
            time.sleep(0.3)
            connection.connect()

            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(GET_UID)

            if (sw1, sw2) != (0x90, 0x00):
                raise RuntimeError(f"Failed to get UID. Status: {hex(sw1)} {hex(sw2)}")

            uid = ''.join(f'{byte:02X}' for byte in response)
            return uid

        except NoCardException:
            time.sleep(0.5)
        except CardConnectionException as e:
            raise RuntimeError(f"Card connection failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Error reading UID: {e}")

    return None


def read_reservation_from_card():
    try:
        r = readers()
        feig_reader = next((reader for reader in r if "FEIG" in str(reader) and "Slot:CL" in str(reader)), None)
        connection = feig_reader.createConnection()
        connection.connect()

        # Read metadata from block 4
        auth_apdu = [0xFF, 0x86, 0x00, 0x00, 0x05,
                     0x01, 0x00, 4, 0x60, 0x00]
        connection.transmit(auth_apdu)

        read_apdu = [0xFF, 0xB0, 0x00, 4, 0x10]
        meta, sw1, sw2 = connection.transmit(read_apdu)
        if (sw1, sw2) != (0x90, 0x00):
            raise RuntimeError(f"Read failed: {hex(sw1)} {hex(sw2)}")

        wait_time = meta[0]
        name_len = meta[1]
        attraction_id = meta[2]

        # Read ride name from blocks 8 and 9
        # Calculate how many blocks are needed
        blocks_needed = (name_len + 15) // 16  # ceil division

        name_bytes = bytearray()
        for i in range(blocks_needed):
            block_num = 8 + i
            auth_apdu = [0xFF, 0x86, 0x00, 0x00, 0x05,
                        0x01, 0x00, block_num, 0x60, 0x00]
            connection.transmit(auth_apdu)

            read_apdu = [0xFF, 0xB0, 0x00, block_num, 0x10]
            data, sw1, sw2 = connection.transmit(read_apdu)
            if (sw1, sw2) != (0x90, 0x00):
                raise RuntimeError(f"Read failed at block {block_num}: {hex(sw1)} {hex(sw2)}")
            name_bytes += bytearray(data)

        ride_name = name_bytes[:name_len].decode("ascii", errors="ignore")

        return {
            "wait_time": wait_time,
            "ride_name": ride_name,
            "attraction_id": attraction_id
        }

    except Exception as e:
        print(f"[ERROR] Failed to read reservation: {e}")
        return None


def start_card_polling(callback, poll_interval=2):
    def poll_loop():
        print("[NFC] Starting card polling loop...")
        while True:
            try:
                if MOCK_NFC:
                    time.sleep(2)  # simulate user delay
                    tag_uid = "MOCK_TAG"
                    reservation = {
                        "command_seq": 1,
                        "command_flag": 0x40,
                        "attraction_id": 1,
                        "wait_time": 1800,
                        "ride_name": "TEST_RIDE"
                    }
                    print("[MOCK] Simulating card tap")
                    callback(tag_uid, reservation)
                    time.sleep(poll_interval)
                    continue

                tag_uid = wait_for_card()

                if not tag_uid:
                    time.sleep(poll_interval)
                    continue


                print(f"[NFC] Card detected: {tag_uid}")
                time.sleep(0.3)

                reservation = read_reservation_from_card()
                if tag_uid and reservation:
                    callback(tag_uid, reservation)
                else:
                    print("[NFC] No reservation or UID found.")

                time.sleep(poll_interval)

            except Exception as e:
                print(f"[NFC] Polling error: {e}")
                traceback.print_exc()
                time.sleep(1)

    thread = threading.Thread(target=poll_loop, daemon=True)
    thread.start()
