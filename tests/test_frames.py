from __future__ import annotations

import pytest

from consult_interface.frames import (
    FrameLayout,
    RegisterNotInHeaderError,
    bytes_to_str,
    invert_byte,
    invert_bytes,
)

# The header the ECU echoes for the test_1 selection: A5 <reg> pairs.
HEADER = bytes.fromhex("A50BA501A508A50CA50DA503A505A509A513A516A517A51AA51CA521")


def test_invert_byte_from_int():
    assert invert_byte(0x5A) == bytearray([0xA5])


def test_invert_byte_from_bytes():
    assert invert_byte(b"\x5a") == bytearray([0xA5])


def test_invert_bytes_round_trips():
    data = b"\xff\xff\xef"
    assert invert_bytes(invert_bytes(data)) == bytearray(data)


def test_invert_bytes_matches_init_handshake():
    assert invert_bytes(b"\xff\xff\xef") == bytearray(b"\x00\x00\x10")


def test_bytes_to_str_hex():
    assert bytes_to_str(b"\x5a\x0b") == "5A 0B"


def test_bytes_to_str_binary():
    assert bytes_to_str(b"\x5a", binary=True) == "01011010"


def test_layout_recovers_register_order():
    layout = FrameLayout.from_header(HEADER)
    assert layout.registers == (
        0x0B, 0x01, 0x08, 0x0C, 0x0D, 0x03, 0x05,
        0x09, 0x13, 0x16, 0x17, 0x1A, 0x1C, 0x21,
    )  # fmt: skip


def test_layout_length_is_param_count():
    assert len(FrameLayout.from_header(HEADER)) == 14


def test_index_of_finds_position():
    layout = FrameLayout.from_header(HEADER)
    assert layout.index_of(0x0B) == 0
    assert layout.index_of(0x21) == 13


def test_index_of_raises_for_absent_register():
    layout = FrameLayout.from_header(HEADER)
    with pytest.raises(RegisterNotInHeaderError):
        layout.index_of(0xFE)


def test_layout_rejects_odd_length_header():
    with pytest.raises(ValueError):
        FrameLayout.from_header(b"\xa5\x0b\xa5")
