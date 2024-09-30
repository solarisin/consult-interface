# test frame decoding
import logging
from pathlib import Path as path
from abc import ABC
from consult_interface.ci_serial import ConsultSerial

logging.getLogger().propagate = True
log = logging.getLogger(__name__)
frame_log = logging.getLogger("frame_log")

class MockConsultSerial(ConsultSerial):
    def __init__(self, port: str, file: path):
        super().__init__(port)
        self._Bps = self._baud / 8 # 9600 / 8 = 1200 Bytes per second
        self._file = file

    def _open(self):
        pass

    def _close(self):
        pass

    def _write(self, data) -> int | None:
        return len(data)

    def _read(self, size: int) -> bytes:
        return b'\x00' * size

    def is_connected(self):
        return True

def test_decode_response(caplog):
    caplog.set_level(logging.DEBUG)
    port = '/dev/ttyUSB0'
    # sent_command =
    response_playback_file = path('../docs/test_data.hex')
    with open(response_playback_file, 'rb') as file:
        data = file.read(28)
        frame_log.debug(data.hex(' ').upper())

    # consult = MockConsultSerial(port, response_playback_file)
    # consult.initialize_ecu()
    # consult.read_ecu_part_number()
    # assert True