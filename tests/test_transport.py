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
