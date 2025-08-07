from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString, toBytes
import random
from datetime import datetime
import time

SCARD_REQUEST_TIMEOUT = 10
SCARD_MAX_READ_LEN = 246
SCARD_MAX_WRITE_LEN = 246
SCARD_NDEF_MSG_SIZE_LEN = 2
SCARD_SW_OKAY = 0x9000

NDEF_RECORD_HEADER_LEN = 18
NDEF_RECORD_PAYLOAD_LEN = 384

REPLYF_INBOOTLOADER = 0x80
REPLYF_RESVNVALID   = 0x40
REPLYF_ADMINICONON  = 0x20

CMDF_ENTERBOOTLOADER = 	0x8000
CMDF_UPDATERESVN =		0x4000
CMDF_USERESVN = 		0x2000
CMDF_SETTIME = 			0x1000
CMDF_GETTIMEREMAINING = 0x0800
CMDF_GETVERSION = 		0x0400
CMDF_SETSHUTDOWNTIME = 	0x0200
CMDF_SHUTDOWNNOW =		0x0100
CMDF_UPDATEICONS = 		0x0080
CMDF_GETBATTERYLEVEL =	0x0040
CMDF_SETLCDTIMEOUT =	0x0020
CMDF_SETOSCSPEED =		0x0010
CMDF_GETTEMP =			0x0008

cardtype = AnyCardType()#ATRCardType(toBytes("3B 80 80 01 01"))
cardrequest = CardRequest(timeout=SCARD_REQUEST_TIMEOUT, cardType=cardtype)
cardservice = ""

def scard_connect():
    global cardservice
    cardservice = cardrequest.waitforcard()
    cardservice.connection.connect()
    
def scard_release():
    global cardservice
    cardservice.connection.release()

def scard_select_app():
    SELECT = [0x00, 0xA4, 0x04, 0x00, 0x07]
    DF_TELECOM = [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01]
    apdu = SELECT + DF_TELECOM
    response, sw1, sw2 = cardservice.connection.transmit(apdu)
    return (sw1<<8) + sw2
    
def scard_select_ndef_file():
    SELECT = [0x00, 0xA4, 0x00, 0x0C, 0x02]
    DF_TELECOM = [0x00, 0x01]
    apdu = SELECT + DF_TELECOM
    response, sw1, sw2 = cardservice.connection.transmit(apdu)
    return (sw1<<8) + sw2
    
def scard_read_ndef_message_length():
    apdu = [0x00, 0xB0, 0x00, 0x00, 0x02]
    response, sw1, sw2 = cardservice.connection.transmit(apdu)
    status = (sw1<<8) + sw2
    if status == SCARD_SW_OKAY:
        return ((response[0]<<8) + response[1]), status
    else:
        print("Failed to read NDEF message length")
        return 0, status
        
def scard_read_ndef_message(address, length):
    i = 0
    message = []
    while i < length:
        if (length - i) > SCARD_MAX_READ_LEN:
            rd_len = SCARD_MAX_READ_LEN
        else:
            rd_len = length - i
        #   Read binary
        offset = address + i
        apdu = [0x00, 0xB0, (offset>>8), (offset & 0xff), rd_len]
        response, sw1, sw2 = cardservice.connection.transmit(apdu)
        if ((sw1<<8) + sw2) != SCARD_SW_OKAY:
            print(f"Failed to read NDEF message {sw1:02X}{sw2:02X}")
            return [], (sw1<<8) + sw2
        else:
            message += response
        i += rd_len
    
    return message, SCARD_SW_OKAY
    
def scard_write_ndef_message(address, data, length):
    i = 0
    while i < length:
        if (length - i) > SCARD_MAX_READ_LEN:
            wr_len = SCARD_MAX_READ_LEN
        else:
            wr_len = length - i
        #   Write binary
        offset = address + i
        apdu = [0x00, 0xD6, (offset>>8), (offset & 0xff), wr_len]
        apdu.extend(data)
        response, sw1, sw2 = cardservice.connection.transmit(apdu)
        if ((sw1<<8) + sw2) != SCARD_SW_OKAY:
            print(f"Failed to write NDEF message {sw1:02X}{sw2:02X}")
            return (sw1<<8) + sw2
        i += wr_len

    return SCARD_SW_OKAY

def read_ndef_message():
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    len, sw = scard_read_ndef_message_length()
    if sw != SCARD_SW_OKAY:
        return
    message, sw = scard_read_ndef_message(0, SCARD_NDEF_MSG_SIZE_LEN+len)
    if sw != SCARD_SW_OKAY:
        return
    #   Print memory
    print("********    Memory Dump    ********")
    line = "0x00:\t"
    for i, byte in enumerate(message):
        if (i > 0)  and (i % 8) == 0:
            print(line)
            line = f"0x{i:02X}:\t{byte:02X}  "
        else:
            line += f'{byte:02X}  '
            
def bcd_to_int(bcd):
    return (((bcd & 0xf0)>>4)*10) + (bcd & 0x0f)

def int_to_bcd(val):
    val = val & 0xff
    return (int((val)/10)<<4) + (int((val)%10) & 0x0F)
    
def use_reseravtion():
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Write read reservation command    
    payload = [0] * 4
    payload[0] = random.randint(0, 255) # random command sequence
    payload[2] = CMDF_USERESVN & 0xff
    payload[3] = CMDF_USERESVN>>8
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 64, payload, len(payload))
    #   Write back message length
    msg_len = NDEF_RECORD_HEADER_LEN + NDEF_RECORD_PAYLOAD_LEN;
    scard_write_ndef_message(0, [(msg_len>>8), (msg_len&0xff)], SCARD_NDEF_MSG_SIZE_LEN)
    
def make_reservation():
    errmsg = ("Attraction ID should be 1 - 255",
            "Ride name too short",
            "Ride name too long (length <= 32 bytes)",
            "Invalid wait time")
    #   Get attraction ID
    print("Please specify attraction ID:")
    try:
        attr_id = int(input())
    except:
        print(errmsg[0])
        return
    if attr_id < 1 or attr_id > 255:
        print(errmsg[0])
    #   Get ride name
    print("Please specify ride name:")
    ride_name = input()
    if len(ride_name) > 32:
        print(errmsg[2])
        return
    elif ride_name == "":
        print(errmsg[1])
        return
    #   Get wait time
    print("Please specify wait time (in seconds):")
    wait_time = int(input())
    if wait_time > 0xFFFF:
        print(errmsg[3])
    #   Write reservation to scard
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Clear message length first
    scard_write_ndef_message(0, [0, 0], SCARD_NDEF_MSG_SIZE_LEN)
    #   Write reservation
    payload = [0] * 8
    payload[0] = random.randint(0, 255) # random command sequence
    payload[2] = CMDF_UPDATERESVN & 0xff
    payload[3] = CMDF_UPDATERESVN>>8
    payload[4] = attr_id
    payload[5] = len(ride_name)
    payload[6] = wait_time & 0xff
    payload[7] = wait_time>>8
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 64, payload, len(payload))
    #   Write ride name
    payload = list(ride_name.encode("ascii"))
    padding = [0] * (32 - len(payload))
    payload.extend(padding)
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 128, payload, len(payload))
    #   Write back message length
    msg_len = NDEF_RECORD_HEADER_LEN + NDEF_RECORD_PAYLOAD_LEN;
    scard_write_ndef_message(0, [(msg_len>>8), (msg_len&0xff)], SCARD_NDEF_MSG_SIZE_LEN)
    
def get_time_remaining():
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Clear message length first
    scard_write_ndef_message(0, [0, 0], SCARD_NDEF_MSG_SIZE_LEN)
    #   Write get time remaining command
    payload = [0] * 4
    payload[0] = random.randint(0, 255) # random command sequence
    payload[2] = CMDF_GETTIMEREMAINING & 0xff
    payload[3] = CMDF_GETTIMEREMAINING>>8
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 64, payload, len(payload))
    #   Write back message length
    msg_len = NDEF_RECORD_HEADER_LEN + NDEF_RECORD_PAYLOAD_LEN;
    scard_write_ndef_message(0, [(msg_len>>8), (msg_len&0xff)], SCARD_NDEF_MSG_SIZE_LEN)
    #   Read remaining time
    time.sleep(1)
    scard_release()
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Read remaining time
    payload = [0] * 3
    payload, sw = scard_read_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 4, len(payload))
    print(f'Remaining time: '+ f'{bcd_to_int(payload[2]):02d}:'
        +f'{bcd_to_int(payload[1]):02d}:' + f'{bcd_to_int(payload[0]):02d}')
    
def set_time():
    #   Get 12/24hr setting
    print("Please select clock time format, [12] or [24]?")
    select = int(input())
    if select != 12 and select != 24:
        print("Invaild clock time format")
        return
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Clear message length first
    scard_write_ndef_message(0, [0, 0], SCARD_NDEF_MSG_SIZE_LEN)
    #   Write current time
    now = datetime.now()
    payload = [0] * 2
    payload[0] = int_to_bcd(now.minute)
    payload[1] = int_to_bcd(now.hour)
    payload[1] = payload[1] | 0x80 if select == 24 else payload[1]
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 72, payload, len(payload))
    #   Write set time command    
    payload = [0] * 4
    payload[0] = random.randint(0, 255) # random command sequence
    payload[2] = CMDF_SETTIME & 0xff
    payload[3] = CMDF_SETTIME>>8
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 64, payload, len(payload))
    #   Write back message length
    msg_len = NDEF_RECORD_HEADER_LEN + NDEF_RECORD_PAYLOAD_LEN;
    scard_write_ndef_message(0, [(msg_len>>8), (msg_len&0xff)], SCARD_NDEF_MSG_SIZE_LEN)
    
def get_version():
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Clear message length first
    scard_write_ndef_message(0, [0, 0], SCARD_NDEF_MSG_SIZE_LEN)
    #   Write get version command
    payload = [0] * 4
    payload[0] = random.randint(0, 255) # random command sequence
    payload[2] = CMDF_GETVERSION & 0xff
    payload[3] = CMDF_GETVERSION>>8
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 64, payload, len(payload))
    #   Write back message length
    msg_len = NDEF_RECORD_HEADER_LEN + NDEF_RECORD_PAYLOAD_LEN;
    scard_write_ndef_message(0, [(msg_len>>8), (msg_len&0xff)], SCARD_NDEF_MSG_SIZE_LEN)
    #   Read remaining time
    time.sleep(1)
    scard_release()
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Read remaining time
    payload = [0] * 4
    payload, sw = scard_read_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 12, len(payload))
    print(f'f/w version: v{payload[0]}.{payload[1]}.{payload[2]}.{payload[3]}')
    
def get_battery_level():
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Clear message length first
    scard_write_ndef_message(0, [0, 0], SCARD_NDEF_MSG_SIZE_LEN)
    #   Write get battery command
    payload = [0] * 4
    payload[0] = random.randint(0, 255) # random command sequence
    payload[2] = CMDF_GETBATTERYLEVEL & 0xff
    payload[3] = CMDF_GETBATTERYLEVEL>>8
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 64, payload, len(payload))
    #   Write back message length
    msg_len = NDEF_RECORD_HEADER_LEN + NDEF_RECORD_PAYLOAD_LEN;
    scard_write_ndef_message(0, [(msg_len>>8), (msg_len&0xff)], SCARD_NDEF_MSG_SIZE_LEN)
    #   Read battery level
    time.sleep(1)
    scard_release()
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Read remaining time
    payload = [0] * 2
    payload, sw = scard_read_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 20, len(payload))
    print(payload)
    
def get_temperature():
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Clear message length first
    scard_write_ndef_message(0, [0, 0], SCARD_NDEF_MSG_SIZE_LEN)
    #   Write get temperature command
    payload = [0] * 4
    payload[0] = random.randint(0, 255) # random command sequence
    payload[2] = CMDF_GETTEMP & 0xff
    payload[3] = CMDF_GETTEMP>>8
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 64, payload, len(payload))
    #   Write back message length
    msg_len = NDEF_RECORD_HEADER_LEN + NDEF_RECORD_PAYLOAD_LEN;
    scard_write_ndef_message(0, [(msg_len>>8), (msg_len&0xff)], SCARD_NDEF_MSG_SIZE_LEN)
    #   Read temperature
    time.sleep(1)
    scard_release()
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Read remaining time
    payload = [0] * 4
    payload, sw = scard_read_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 24, len(payload))
    print(payload)
    
def set_icons():
    print('Please set icon flags:\n' + '  bit0: premium icon\n'
            + '  bit1: group icon\n' + '  bit2: admin icon\n')
    print('Icons to set:')
    flags = int(input())
    flags &= 0x07
    scard_connect()
    if scard_select_app() != SCARD_SW_OKAY:
        return
    if scard_select_ndef_file() != SCARD_SW_OKAY:
        return
    #   Clear message length first
    scard_write_ndef_message(0, [0, 0], SCARD_NDEF_MSG_SIZE_LEN)
    #   Write icon flags
    payload = [flags]
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 76, payload, len(payload))
    #   Write set time command    
    payload = [0] * 4
    payload[0] = random.randint(0, 255) # random command sequence
    payload[2] = CMDF_UPDATEICONS & 0xff
    payload[3] = CMDF_UPDATEICONS>>8
    scard_write_ndef_message(SCARD_NDEF_MSG_SIZE_LEN + NDEF_RECORD_HEADER_LEN + 64, payload, len(payload))
    #   Write back message length
    msg_len = NDEF_RECORD_HEADER_LEN + NDEF_RECORD_PAYLOAD_LEN;
    scard_write_ndef_message(0, [(msg_len>>8), (msg_len&0xff)], SCARD_NDEF_MSG_SIZE_LEN)
    
OP_DESC_LIST = (
    "Read NDEF message",
    "Use reservation",
    "Make reservation",
    "Get time remaining",
    "Set time",
    "Get version",
    "Read battery level",
    "Read temperature",
    "Set icons",
)

OP_FUNC_LIST = (
    read_ndef_message,
    use_reseravtion,
    make_reservation,
    get_time_remaining,
    set_time,
    get_version,
    get_battery_level,
    get_temperature,
    set_icons,
)

def main():
    #   Print Menu
    print('Please select an operation:\n')
    for i, desc in enumerate(OP_DESC_LIST):
        print("  "+str(i+1)+". "+desc)
    #   Get user input
    print("\nYour choice: ")
    err = "\nPlease select from 1 to {}.".format(len(OP_DESC_LIST))
    try:
        sel = int(input())
    except:
        print(err)
        return
    if sel < 1 or sel > len(OP_DESC_LIST):
        print(err)
        return
    #   Call handler
    print("")
    OP_FUNC_LIST[sel-1]()

if __name__ == "__main__":
    main()
