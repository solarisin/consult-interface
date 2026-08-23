"""CONSULT protocol logic, independent of how bytes are moved.

Sequence:
  1. init      -- write FF FF EF, expect the byte-inverted reply
  2. select    -- write 5A <reg> per parameter, terminated by F0
  3. header    -- the ECU echoes the selection with 5A markers inverted to A5
  4. stream    -- repeating FF <data_len> <data bytes...>
  5. stop      -- write 30
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from .definition import ConsultDefinition, ParamID
from .frames import FrameLayout, FrameParser, invert_bytes
from .params import ParamSpec
from .transport import Transport

log = logging.getLogger(__name__)


class InitializeFailedError(ValueError):
    """The ECU did not answer the init handshake with the inverted command."""


class ConsultSession:
    """Speaks CONSULT over any Transport."""

    def __init__(self, transport: Transport, definition: ConsultDefinition | None = None) -> None:
        self._transport = transport
        self._definition = definition or ConsultDefinition()
        self._initialized = False

    @property
    def definition(self) -> ConsultDefinition:
        return self._definition

    def _ensure_open(self) -> None:
        if not self._transport.is_connected():
            self._transport.open()

    def initialize(self) -> bool:
        """Perform the FF FF EF handshake."""
        self._ensure_open()

        command = bytes(self._definition.init)
        self._transport.write(command)

        expected = bytes(invert_bytes(command))
        response = self._transport.read(len(expected))
        if response != expected:
            raise InitializeFailedError(
                f"unexpected init response: {response.hex(' ').upper()} "
                f"(expected {expected.hex(' ').upper()})"
            )
        self._initialized = True
        return True

    def select(self, param_ids: Iterable[ParamID]) -> FrameParser:
        """Request parameters and return a parser built from the ECU's echo.

        Replaying a capture file skips `initialize` -- captures start after the
        command was sent -- so this opens the transport itself if needed.
        """
        self._ensure_open()

        # Narrow explicitly -- mypy --strict cannot follow Optional through a
        # list comprehension guarded by any().
        specs: list[ParamSpec] = []
        for pid in param_ids:
            spec = self._definition.get_parameter(pid)
            if spec is None:
                raise ValueError(f"unknown ParamID: {pid!r}")
            specs.append(spec)

        command = bytearray()
        for spec in specs:
            command.append(self._definition.cmd_register_param)
            command.append(spec.register)
        command.append(self._definition.start_stream)
        self._transport.write(bytes(command))

        # The echo is one A5 <reg> pair per selected register.
        header = self._transport.read(len(command) - 1)
        layout = FrameLayout.from_header(header)
        return FrameParser(layout, specs)

    def read_frame(self, parser: FrameParser) -> dict[ParamID, float | int]:
        """Read and decode exactly one frame."""
        frame = self._transport.read(len(parser.layout) + 2)
        return parser.decode(frame)

    def stop(self) -> None:
        """Tell the ECU to stop streaming."""
        self._transport.write(bytes([self._definition.stop_stream]))
