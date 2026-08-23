# consult-interface

Host-side implementation of the Nissan CONSULT diagnostic protocol — 9600-baud
serial to an ECU over a USB adapter.

## Quick start

```bash
uv sync
uv run pytest
```

## Reading a capture without hardware

`CaptureTransport` replays a recorded `.hex` capture through the same interface
the real serial link uses. Because the ECU's header echo defines the frame
layout, you must select the same parameters, in the same order, that produced
the capture:

```python
from pathlib import Path

from consult_interface import CaptureTransport, ConsultSession, ParamID

# The selection that produced docs/test_data.hex.
SELECTION = [
    ParamID.VEHICLE_SPEED, ParamID.ENGINE_SPEED_HR, ParamID.COOLANT_TEMP,
    ParamID.BATTERY_VOLTAGE, ParamID.TPS, ParamID.ENGINE_SPEED_LR,
    ParamID.MAF_VOLTAGE, ParamID.O2_VOLTAGE_LH, ParamID.CLSD_THL_POS,
    ParamID.IGNITION_TIMING, ParamID.AAC_VALVE, ParamID.AF_ALPHA_LH,
    ParamID.AF_ALPHA_SELFLEARN_LH, ParamID.RH_BANK_LEAN,
]

session = ConsultSession(CaptureTransport(Path("docs/test_data.hex")))
parser = session.select(SELECTION)
print(session.read_frame(parser))
# {<ParamID.VEHICLE_SPEED: 7>: 0, <ParamID.ENGINE_SPEED_HR: 0>: 700.0, ...}
```

## Talking to a real ECU

```python
from consult_interface import ConsultSession, ParamID, SerialTransport

session = ConsultSession(SerialTransport("/dev/ttyUSB0"))
session.initialize()                      # FF FF EF handshake
parser = session.select([ParamID.ENGINE_SPEED_HR, ParamID.COOLANT_TEMP])
try:
    while True:
        print(session.read_frame(parser))
finally:
    session.stop()
```

Protocol reference material lives in `docs/` — **Issue 7 is the newest**.
