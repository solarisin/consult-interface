import serial
import time
from consult_viewer import consult_interface as ci

# used `socat -d -d pty,raw,echo=0 pty,raw,echo=0` to start a loopback
# result:
# 2024/07/31 13:39:33 socat[511425] N PTY is /dev/pts/9
# 2024/07/31 13:39:33 socat[511425] N PTY is /dev/pts/10
# 2024/07/31 13:39:33 socat[511425] N starting data transfer loop with FDs [5,5] and [7,7]

write_port = serial.Serial('/dev/pts/6', baudrate=9600, timeout=None)
read_port = serial.Serial('/dev/pts/7', baudrate=9600, timeout=None)

# this is the original command from an example, but 0x13 doesn't match anything on the specs. also skipping 21 since
# idk really what it is, although it is documented
# write_port.write(b'\x5A\x0B\x5A\x01\x5A\x08\x5A\x0C\x5A\x0D\x5A\x03\x5A\x05\x5A\x09\x5A\x13\x5A\x16\x5A\x17\x5A\x1A\x5A\x1C\x5A\x21\xF0')

print()
print('------------------------------------------')
print('------- Writing bytes to loopback --------')
print('------------------------------------------')
write_bytes = b'\x5A\x0B\x5A\x01\x5A\x08\x5A\x0C\x5A\x0D\x5A\x03\x5A\x05\x5A\x09\x5A\x16\x5A\x17\x5A\x1A\x5A\x1C\xF0'
write_port.write(write_bytes)

# sleep for 1 second
time.sleep(1)
print(f'There are {read_port.in_waiting} bytes available to read.')
incomingData = read_port.read_all()
if incomingData:
    for byte in incomingData:
        if byte == 0x5A or byte == 0xF0:
            print()
        # print in pretty hex
        print(f'{byte:02X}', end=' ')
else:
    print('   No data received. Is the loopback open?')

print()
print()
print('------------------------------------------')
print('-- Generating command from paramID list --')
print('------------------------------------------')
param_id_list = [
    ci.ParamID.VEHICLE_SPEED,
    ci.ParamID.ENGINE_SPEED_HR,
    ci.ParamID.COOLANT_TEMP,
    ci.ParamID.BATTERY_VOLTAGE,
    ci.ParamID.TPS,
    ci.ParamID.ENGINE_SPEED_LR,
    ci.ParamID.MAF_VOLTAGE,
    ci.ParamID.O2_VOLTAGE_LH,
    ci.ParamID.IGNITION_TIMING,
    ci.ParamID.AAC_VALVE,
    ci.ParamID.AF_ALPHA_LH,
    ci.ParamID.AF_ALPHA_SELFLEARN_LH

]
command = ci.params_to_command(param_id_list)
for b in command:
    if b == 0x5A or b == 0xF0:
        print()
    print(f'{b:02X}', end=' ')

print()

if write_bytes == command:
    print('Generated command matches sample!')

print()
print('------------------------------------------')
print('------------ Decoding Command ------------')
print('------------------------------------------')

params = ci.command_to_params(command)
x = 0
for byte in write_bytes:
    if byte == 0x5A:
        continue
    if byte == 0xF0:
        print(f'{byte:02X}')
        break
    # print in pretty hex, followed by the decoded name
    print(f'5A {byte:02X} - {params[x].name}', end=' ')
    print()
    x += 1
