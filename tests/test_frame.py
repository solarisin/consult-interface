# test frame decoding
from pathlib import Path as path
from abc import ABC
from consult_interface.ci_serial import ConsultSerial

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