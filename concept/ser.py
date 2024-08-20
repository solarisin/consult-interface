#!/usr/bin/env python

import serial
import time


class InvalidFrameError(ValueError):
    pass


class InitializeFailedError(ValueError):
    pass


class InvalidAckError(ValueError):
    pass


# def bytes_to_str(b: bytes, binary=False):
#     b_str = b.hex().upper()
#     return ' '.join(b_str[i:i + 2] for i in range(0, len(b_str), 2))

def bytes_to_str(b: bytes, binary=False):
    if binary:
        return ' '.join(f'{b[i]:08b}' for i in range(len(b)))
    b_str = b.hex().upper()
    return ' '.join(b_str[i:i + 2] for i in range(0, len(b_str), 2))


def invert_bytes(data: bytes | bytearray | int) -> bytearray | int:
    if isinstance(data, int):
        return ~data & 0xFF
    return bytearray([(~b & 0xFF) for b in data])


def process_read_ecu_part_number(frame: bytearray):
    check_bytes = 2
    data_bytes = 22
    frame_name = "read_ecu_part_number"
    frame_bytes = check_bytes + data_bytes
    data = frame[check_bytes:]

    if not len(frame) == frame_bytes:
        raise InvalidFrameError(
            f'{frame_name} frame contains {len(frame)} bytes, not {frame_bytes}: {bytes_to_str(frame)}')
    if not frame[0:check_bytes] == b'\xFF\x16':
        raise InvalidFrameError("Invalid check bytes")
    print(f'ECU Part Number: {data[2:4].hex()} 23710-{frame[19:].decode()}')


def process_frame(cmd: bytes, frame: bytearray):
    if cmd == b'\xD0':
        process_read_ecu_part_number(frame)


def initialize(port: serial.Serial):
    port.write(b'\xFF\xFF\xEF')
    init = port.read(3)
    if not init == b'\x00\x00\x10':
        raise InitializeFailedError(f"Received unexpected init response '{bytes_to_str(init)}'")


def read_ecu_part_number(port: serial.Serial):
    ecu_part_number_cmd = b'\xD0'
    ecu_part_number_ack = invert_bytes(ecu_part_number_cmd)
    cmd_delimiter = b'\xF0'
    cmd_stop = b'\x30'
    cmd_stop_ack = invert_bytes(cmd_stop)
    port.write(ecu_part_number_cmd + cmd_delimiter)

    ack = port.read(1)
    if not ack == ecu_part_number_ack:
        raise InvalidAckError(
            f"Received unexpected acknowledge byte '{ack.hex(' ')}', expected '{ecu_part_number_ack.hex(' ')}'")
    port.write(cmd_stop)
    data = port.read(24)
    process_frame(ecu_part_number_cmd, data)
    stop_ack = port.read(1)
    if stop_ack != cmd_stop_ack:
        raise InvalidAckError(f"Unexpected stop ack received: {stop_ack.hex(' ')}")


def read_dtc(port: serial.Serial):
    read_dtc_cmd = b'\xD1'
    read_dtc_ack = invert_bytes(read_dtc_cmd)
    cmd_delimiter = b'\xF0'
    cmd_stop = b'\x30'
    cmd_stop_ack = invert_bytes(cmd_stop)

    port.write(read_dtc_cmd + cmd_delimiter)
    ack = port.read(1)
    if not ack == read_dtc_ack:
        raise InvalidAckError(
            f"Received unexpected acknowledge byte '{ack.hex(' ')}', expected '{read_dtc_ack.hex(' ')}'")
    port.write(cmd_stop)

    buf = bytearray()
    data = port.read(1)
    while data != cmd_stop_ack:
        buf += data
        data = port.read(1)
    if buf[0] != 0xFF:
        raise InvalidFrameError("Unexpected starting byte in dtc frame data: f{buf[0]}")
    data_size = buf[1]
    if data_size == 2 and buf[2] == 0x55:
        print("No DTCs")
    else:
        print(f"ECU reports {data_size} bytes of DTC codes: {buf[2:]}")


port = serial.Serial("/dev/ttyUSB0", 9600, timeout=None, xonxoff=False, rtscts=False, dsrdtr=False)

initialize(port)

read_ecu_part_number(port)

read_dtc(port)

cmd_stop = b'\x30'
cmd_stop_ack = invert_bytes(cmd_stop)

cmd_ecu_param = 0x5A
cmd_delim = 0xF0

params = [
    0x0C,
    # 0x0D
]

send_data = bytearray()

for p in params:
    send_data.append(cmd_ecu_param)
    send_data.append(p)

send_data.append(cmd_delim)

port.write(send_data)

for p in params:
    p_ack = port.read(2)
    if p_ack[0] != invert_bytes(cmd_ecu_param) or p_ack[1] != p:
        print(f"invalid ack for {p}")
port.write(cmd_stop)

buf = bytearray()
data = port.read(1)
while data != cmd_stop_ack:
    buf += data
    data = port.read(1)
print(bytes_to_str(buf))
volts_unscaled = buf[2]
print(f"Voltage: {volts_unscaled * 80} mV")

# cmd_stop = b'\x30'
# cmd_stop_ack = invert_bytes(cmd_stop)

# port.write(b'\x5A\x0C\xF0')
# ack = port.read(2)
# print(f"ack: {bytes_to_str(ack)}")

# volts = 0
# while True:
#     if port.in_waiting > 30:
#         print("Buffer overflowing")
#     data = port.read(3)
#     new_volts = (int(data[2]) * 80.0)/1000.0
#     if new_volts != volts:
#         volts = new_volts
#         print(f"Voltage: {volts} V")


#
# bytes_written = port.write(b'\xFF\xFF\xEF')
# print(f"Wrote {bytes_written} bytes to {port.port}")
# time.sleep(3)
#
# req_bytes = 1
# data = port.read(req_bytes)
# if (len(data) == req_bytes):
#     print(f"Successfully read {len(data)} byte(s): '{data:X02}'")
# elif (len(data) != 0):
#     print(
#         f"Timed out waiting for {req_bytes} byte(s) of data after {port.timeout} seconds - {len(data)} bytes were read: '{data}'")
# else:
#     print(f"Timed out waiting for {req_bytes} byte(s) of data data after {port.timeout} seconds - no bytes were read.")