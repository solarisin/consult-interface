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

def test_decode_response(caplog, data_registry):
    caplog.set_level(logging.DEBUG)
    log.debug("Test decoding of response frame")
    data_entry_id = "test_1"

    test_data = data_registry.get(data_entry_id)
    if test_data is None:
        log.error(f"Data entry '{data_entry_id}' not found")
        assert False

    log.debug(f"  Sent Command: {test_data.command.hex(' ').upper()}")
    log.debug(f"  Capture File: {test_data.capture_file}")

    with (open(test_data.capture_file, 'rb') as file):
        # read until we find the frame start flag (0xFF), this is the command error check
        command_check = bytearray()
        while byte := file.read(1):
            if len(byte) == 0:
                raise ValueError("End of file reached before command check complete")
            if byte == b'\xFF':
                break
            command_check.append(byte[0])
        frame_log.debug(f"Command check response: {command_check.hex(' ').upper()}")

        # TODO verify this response matches the command sent

        first_frame = bytearray()
        first_frame.append(0xFF)
        # read the next byte, this is the size of the data in the frame
        frame_size_byte = file.read(1)
        if len(frame_size_byte) == 0:
            raise ValueError("End of file reached before first frame size byte read")
        frame_data_size = frame_size_byte[0]
        frame_size = frame_data_size + 2
        first_frame.append(frame_size)
        log.debug(f"Frame Size: {frame_size}")

        # read the rest of the first frame
        first_frame_data = file.read(frame_data_size)
        if len(first_frame_data) == 0:
            raise ValueError("End of file reached before first frame data read")
        first_frame.extend(first_frame_data)
        frame_log.debug(f" 1: {first_frame.hex(' ').upper()}")

        # read the rest of the frames in the file
        n = 1
        while frame := file.read(frame_size):
            n+=1
            if len(frame) != frame_size:
                log.debug(f"End of file reached after {n} frames")
                break
            if n < 100:
                frame_log.debug(f"{n:2}: {frame.hex(' ').upper()}")

    # consult = MockConsultSerial(port, response_playback_file)
    # consult.initialize_ecu()
    # consult.read_ecu_part_number()
    # assert True