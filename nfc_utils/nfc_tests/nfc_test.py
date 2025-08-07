from smartcard.System import readers
from smartcard.Exceptions import NoCardException

r = readers()
print("Available readers:", r)

if r:
    reader = r[2]  # Adjust index if needed
    connection = reader.createConnection()
    try:
        connection.connect()
        print(f"Connected to: {reader}")

        # Send APDU command to get UID
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(GET_UID)
        print("UID:", response)
        print("Status:", hex(sw1), hex(sw2))

    except NoCardException:
        print("No card detected. Please place a card on the reader.")
else:
    print("No PC/SC readers found.")
