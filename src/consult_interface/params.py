"""Immutable descriptions of ECU parameters.

A ParamSpec says what a register MEANS. It never holds a value -- decoding a
frame returns values (see frames.FrameParser) rather than mutating shared
state, which is what makes decode calls order-independent and thread-safe.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from .frames import FRAME_START, FrameLayout, RegisterNotInHeaderError

if TYPE_CHECKING:
    from .definition import ParamID

log = logging.getLogger(__name__)


def _data_bytes(frame: bytes, layout: FrameLayout) -> bytes:
    """Strip the `FF <len>` prefix, logging (not raising) on malformed frames.

    PRESERVED QUIRK: sanity failures log and continue, matching the original
    pre-0.2 EcuParam.sanity_check (removed; see git history).
    """
    if frame[0] != FRAME_START:
        log.error("Invalid frame start byte: %s", frame.hex(" "))
    if frame[1] != len(layout):
        log.error(
            "Frame declares %d data bytes but header lists %d registers: %s",
            frame[1],
            len(layout),
            frame.hex(" "),
        )
    return frame[2:]


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """Base description of one ECU parameter."""

    param_id: ParamID
    name: str
    unit: str = ""
    scale: float = 1.0
    offset: float = 0.0

    @property
    def registers(self) -> tuple[int, ...]:
        """Every register this parameter reads (MSB first for dual params)."""
        raise NotImplementedError

    @property
    def register(self) -> int:
        """The single register identifying this parameter (LSB for dual)."""
        raise NotImplementedError

    def decode(self, layout: FrameLayout, frame: bytes) -> float | int:
        """Read this parameter's value out of one frame."""
        raise NotImplementedError

    def _scaled(self, unscaled: int) -> float:
        return (unscaled * self.scale) + self.offset


@dataclass(frozen=True, slots=True)
class SingleParam(ParamSpec):
    """One register, scaled and offset."""

    register_addr: int = 0

    @property
    @override
    def registers(self) -> tuple[int, ...]:
        return (self.register_addr,)

    @property
    @override
    def register(self) -> int:
        return self.register_addr

    @override
    def decode(self, layout: FrameLayout, frame: bytes) -> float | int:
        data = _data_bytes(frame, layout)
        return self._scaled(data[layout.index_of(self.register_addr)])


@dataclass(frozen=True, slots=True)
class DualParam(ParamSpec):
    """Two registers combined as `msb << 8 | lsb`."""

    register_msb: int = 0
    register_lsb: int = 0

    @property
    @override
    def registers(self) -> tuple[int, ...]:
        return (self.register_msb, self.register_lsb)

    @property
    @override
    def register(self) -> int:
        return self.register_lsb

    @override
    def decode(self, layout: FrameLayout, frame: bytes) -> float | int:
        data = _data_bytes(frame, layout)

        # PRESERVED QUIRK: a missing half substitutes 0; only both missing raises.
        msb_found = lsb_found = True
        try:
            msb = data[layout.index_of(self.register_msb)]
        except RegisterNotInHeaderError:
            msb, msb_found = 0, False
        try:
            lsb = data[layout.index_of(self.register_lsb)]
        except RegisterNotInHeaderError:
            lsb, lsb_found = 0, False

        if not msb_found and not lsb_found:
            raise RegisterNotInHeaderError(
                f"neither register 0x{self.register_msb:02X} nor "
                f"0x{self.register_lsb:02X} is in the header layout"
            )
        return self._scaled((msb << 8) + lsb)


@dataclass(frozen=True, slots=True)
class BitParam(ParamSpec):
    """One bit of a status register."""

    register_addr: int = 0
    bit: int = 0

    @property
    @override
    def registers(self) -> tuple[int, ...]:
        return (self.register_addr,)

    @property
    @override
    def register(self) -> int:
        return self.register_addr

    @override
    def decode(self, layout: FrameLayout, frame: bytes) -> float | int:
        # PRESERVED QUIRK: returns the raw bit, ignoring scale and offset.
        data = _data_bytes(frame, layout)
        return (data[layout.index_of(self.register_addr)] >> self.bit) & 1
