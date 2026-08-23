"""Frame-level primitives for the CONSULT protocol.

The ECU echoes a register selection back with the 0x5A marker bytes inverted
to 0xA5 and the register bytes unchanged:

    A5 <reg> A5 <reg> ...

That echo IS the frame layout descriptor: data bytes in each subsequent
`FF <len> <data...>` frame appear in exactly the order the header lists.
"""

from __future__ import annotations

from dataclasses import dataclass

HEADER_MARKER = 0xA5
FRAME_START = 0xFF


class RegisterNotInHeaderError(ValueError):
    """A register was requested that the ECU's header echo does not list."""


def invert_byte(byte: bytes | bytearray | int) -> bytearray:
    """Bitwise-invert a single byte. The ECU acks commands with their inverse."""
    if isinstance(byte, int):
        return bytearray([~byte & 0xFF])
    return bytearray([~byte[0] & 0xFF])


def invert_bytes(data: bytes | bytearray) -> bytearray:
    """Bitwise-invert every byte in a sequence."""
    return bytearray((~b & 0xFF) for b in data)


def bytes_to_str(b: bytes, binary: bool = False) -> str:
    """Render bytes for logging: '5A 0B' by default, '01011010' if binary."""
    if binary:
        return " ".join(f"{byte:08b}" for byte in b)
    hex_str = b.hex().upper()
    return " ".join(hex_str[i : i + 2] for i in range(0, len(hex_str), 2))


@dataclass(frozen=True, slots=True)
class FrameLayout:
    """The ordered registers a frame's data bytes correspond to."""

    registers: tuple[int, ...]

    @classmethod
    def from_header(cls, header: bytes) -> FrameLayout:
        """Parse an `A5 <reg> A5 <reg> ...` echo into its register order."""
        if len(header) % 2 != 0:
            raise ValueError(
                f"header must be an even number of bytes, got {len(header)}: {bytes_to_str(header)}"
            )
        return cls(tuple(header[1::2]))

    def index_of(self, register: int) -> int:
        """Position of `register` in the frame's data bytes."""
        try:
            return self.registers.index(register)
        except ValueError as exc:
            raise RegisterNotInHeaderError(
                f"register 0x{register:02X} not in header layout "
                f"{[f'0x{r:02X}' for r in self.registers]}"
            ) from exc

    def __len__(self) -> int:
        return len(self.registers)
