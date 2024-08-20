#!/usr/bin/env python

import serial
import time

port = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.5)

def bytes_to_str(b: bytes):
    b_str = b.hex().upper()
    return ' '.join(b_str[i:i + 2] for i in range(0, len(b_str), 2))


snd = 0
while (True):
    send = b'\xFF\xFF\xEF'
    print(f"Sending data: {bytes_to_str(send)}")
    port.write(send)
    time.sleep(0.2)
    waiting = port.in_waiting
    while (waiting):
        # read data and change endianness
        data = port.read(port.in_waiting)
        data = data[::-1]

        print(f"Received data: {bytes_to_str(data)}")
        time.sleep(0.5)
        waiting = port.in_waiting
    time.sleep(.1)






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