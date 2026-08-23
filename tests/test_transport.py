from __future__ import annotations

from pathlib import Path

import pytest

from consult_interface.transport import CaptureTransport, Transport


@pytest.fixture
def capture_path(project_root_path) -> Path:
    return Path(project_root_path) / "docs" / "test_data.hex"


def test_capture_transport_satisfies_the_protocol(capture_path):
    assert isinstance(CaptureTransport(capture_path), Transport)


def test_capture_transport_reads_requested_size(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    assert len(t.read(4)) == 4
    t.close()


def test_capture_transport_reads_sequentially(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    first, second = t.read(2), t.read(2)
    t.close()

    t2 = CaptureTransport(capture_path)
    t2.open()
    assert t2.read(4) == first + second
    t2.close()


def test_capture_transport_returns_short_read_at_eof(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    t.read(capture_path.stat().st_size - 2)
    assert len(t.read(100)) == 2
    t.close()


def test_capture_transport_writes_are_accepted_and_counted(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    assert t.write(b"\xff\xff\xef") == 3
    t.close()


def test_capture_transport_records_what_was_written(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    t.write(b"\xff\xff\xef")
    t.write(b"\x30")
    t.close()
    assert t.written == b"\xff\xff\xef\x30"


def test_read_before_open_raises(capture_path):
    with pytest.raises(RuntimeError):
        CaptureTransport(capture_path).read(1)


def test_is_connected_tracks_open_and_close(capture_path):
    t = CaptureTransport(capture_path)
    assert not t.is_connected()
    t.open()
    assert t.is_connected()
    t.close()
    assert not t.is_connected()


from consult_interface.definition import ParamID  # noqa: E402
from consult_interface.session import ConsultSession, InitializeFailedError  # noqa: E402


class ScriptedTransport:
    """Transport returning canned responses, for handshake tests."""

    def __init__(self, responses: bytes) -> None:
        self._responses = responses
        self._pos = 0
        self.written = bytearray()
        self._open = False

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def read(self, size: int) -> bytes:
        chunk = self._responses[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    def write(self, data: bytes) -> int | None:
        self.written.extend(data)
        return len(data)

    def is_connected(self) -> bool:
        return self._open


def test_initialize_sends_handshake_and_accepts_inverted_reply():
    t = ScriptedTransport(b"\x00\x00\x10")
    assert ConsultSession(t).initialize() is True
    assert bytes(t.written) == b"\xff\xff\xef"


def test_initialize_raises_on_wrong_reply():
    t = ScriptedTransport(b"\xde\xad\xbe")
    with pytest.raises(InitializeFailedError):
        ConsultSession(t).initialize()


def test_select_writes_register_command_terminated_by_start_stream():
    header = bytes.fromhex("A50BA508")
    t = ScriptedTransport(header)
    session = ConsultSession(t)
    session.select([ParamID.VEHICLE_SPEED, ParamID.COOLANT_TEMP])
    assert bytes(t.written) == b"\x5a\x0b\x5a\x08\xf0"


def test_select_returns_parser_matching_the_echoed_header():
    header = bytes.fromhex("A50BA508")
    session = ConsultSession(ScriptedTransport(header))
    parser = session.select([ParamID.VEHICLE_SPEED, ParamID.COOLANT_TEMP])
    assert parser.layout.registers == (0x0B, 0x08)


def test_stop_writes_stop_byte():
    t = ScriptedTransport(b"")
    ConsultSession(t).stop()
    assert bytes(t.written) == b"\x30"


def test_scripted_transport_satisfies_the_protocol():
    from consult_interface.transport import Transport as T

    assert isinstance(ScriptedTransport(b""), T)
