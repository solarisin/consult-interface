"""Byte transport for the CONSULT protocol.

Transport moves bytes and knows nothing about the protocol. Protocol logic
lives in session.ConsultSession.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import IO, Protocol, runtime_checkable

import serial

log = logging.getLogger(__name__)

DEFAULT_BAUD = 9600


@runtime_checkable
class Transport(Protocol):
    """Anything that can move bytes to and from an ECU."""

    def open(self) -> None: ...

    def close(self) -> None: ...

    def read(self, size: int) -> bytes: ...

    def write(self, data: bytes) -> int | None: ...

    def is_connected(self) -> bool: ...


class SerialTransport:
    """Real 9600-baud serial connection over a USB adapter."""

    def __init__(self, port: str, baud: int = DEFAULT_BAUD) -> None:
        self._port = port
        self._baud = baud
        self._serial = serial.Serial(
            port, baud, timeout=None, xonxoff=False, rtscts=False, dsrdtr=False
        )

    def open(self) -> None:
        if not self._serial.is_open:
            self._serial.open()

    def close(self) -> None:
        self._serial.close()

    def read(self, size: int) -> bytes:
        return bytes(self._serial.read(size))

    def write(self, data: bytes) -> int | None:
        written: int | None = self._serial.write(data)
        return written

    def is_connected(self) -> bool:
        return bool(self._serial.is_open)

    @property
    def raw(self) -> serial.Serial:
        """The underlying pyserial handle, for ReadParamFramesThread."""
        return self._serial


class CaptureTransport:
    """Replays a raw ECU capture file.

    Capture files start AFTER the command was sent and contain no init
    sequence, so writes are accepted, recorded, and otherwise ignored.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._handle: IO[bytes] | None = None
        self._written = bytearray()

    def open(self) -> None:
        if self._handle is None:
            self._handle = self._path.open("rb")

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def read(self, size: int) -> bytes:
        if self._handle is None:
            raise RuntimeError("CaptureTransport.read() before open()")
        return self._handle.read(size)

    def write(self, data: bytes) -> int | None:
        self._written.extend(data)
        return len(data)

    def is_connected(self) -> bool:
        return self._handle is not None

    @property
    def written(self) -> bytes:
        """Every byte written since construction, for assertions."""
        return bytes(self._written)


class ReadParamFramesThread(threading.Thread):
    """Pumps fixed-size frames off a transport into a callback."""

    def __init__(
        self,
        transport: Transport,
        frame_bytes: int,
        process_frame: Callable[[bytes], None],
    ) -> None:
        super().__init__(daemon=True)
        self._transport = transport
        self._frame_size = frame_bytes
        self._running = False
        self.process_frame = process_frame

    def run(self) -> None:
        # BUGFIX: the original tested `if not self._port.open()`, but
        # Serial.open() returns None, so that branch always fired.
        opened_here = False
        if not self._transport.is_connected():
            self._transport.open()
            opened_here = True

        self._running = True
        try:
            while self._running:
                frame = self._transport.read(self._frame_size)
                if len(frame) == self._frame_size:
                    self.process_frame(frame)
        finally:
            if opened_here:
                self._transport.close()

    def stop(self) -> None:
        self._running = False
