from __future__ import annotations

from dataclasses import FrozenInstanceError

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


from consult_interface.definition import ParamID  # noqa: E402
from consult_interface.frames import FrameParser  # noqa: E402
from consult_interface.params import BitParam, DualParam, SingleParam  # noqa: E402

# 14 data bytes matching HEADER's register order, prefixed with FF <len>.
FRAME = bytes(
    [0xFF, 0x0E, 0x00, 0x38, 0x7F, 0xB2, 0x17, 0x6B, 0xD0,
     0x1C, 0x01, 0x68, 0x4C, 0x64, 0x76, 0x00]
)  # fmt: skip


def test_single_param_scales_and_offsets():
    spec = SingleParam(ParamID.COOLANT_TEMP, "Coolant Temp", "C", 1, -50, register_addr=0x08)
    layout = FrameLayout.from_header(HEADER)
    assert spec.decode(layout, FRAME) == 0x7F - 50


def test_dual_param_combines_msb_and_lsb():
    spec = DualParam(
        ParamID.ENGINE_SPEED_HR, "Engine Speed HR", "RPM", 12.5, 0,
        register_msb=0x00, register_lsb=0x01,
    )  # fmt: skip
    layout = FrameLayout.from_header(HEADER)
    # 0x00 is absent from HEADER so the MSB substitutes 0; LSB 0x01 -> 0x38
    assert spec.decode(layout, FRAME) == 0x38 * 12.5


def test_dual_param_raises_only_when_both_registers_absent():
    spec = DualParam(
        ParamID.INJECTOR_TIME_RH, "Injector Time RH", "ms", 0.01, 0,
        register_msb=0x22, register_lsb=0x23,
    )  # fmt: skip
    layout = FrameLayout.from_header(HEADER)
    with pytest.raises(RegisterNotInHeaderError):
        spec.decode(layout, FRAME)


def test_bit_param_returns_raw_bit_ignoring_scale():
    spec = BitParam(ParamID.CLSD_THL_POS, "CLSD/THL POS", register_addr=0x13, bit=0)
    layout = FrameLayout.from_header(HEADER)
    assert spec.decode(layout, FRAME) == 1


def test_bit_param_reads_the_right_bit():
    spec = BitParam(ParamID.AC_ON, "A/C On", register_addr=0x13, bit=4)
    layout = FrameLayout.from_header(HEADER)
    assert spec.decode(layout, FRAME) == 0


def test_single_param_raises_for_absent_register():
    spec = SingleParam(ParamID.EGT, "EGT", "mV", 20, 0, register_addr=0x12)
    layout = FrameLayout.from_header(HEADER)
    with pytest.raises(RegisterNotInHeaderError):
        spec.decode(layout, FRAME)


def test_param_specs_are_frozen():
    spec = SingleParam(ParamID.COOLANT_TEMP, "Coolant Temp", "C", 1, -50, register_addr=0x08)
    with pytest.raises(FrozenInstanceError):
        spec.scale = 99  # type: ignore[misc]


def test_frame_parser_decodes_all_specs():
    layout = FrameLayout.from_header(HEADER)
    specs = [
        SingleParam(ParamID.COOLANT_TEMP, "Coolant Temp", "C", 1, -50, register_addr=0x08),
        SingleParam(ParamID.VEHICLE_SPEED, "Vehicle Speed", "km/h", 2, 0, register_addr=0x0B),
    ]
    result = FrameParser(layout, specs).decode(FRAME)
    assert result == {ParamID.COOLANT_TEMP: 0x7F - 50, ParamID.VEHICLE_SPEED: 0}


def test_frame_parser_propagates_missing_register():
    layout = FrameLayout.from_header(HEADER)
    specs = [SingleParam(ParamID.EGT, "EGT", "mV", 20, 0, register_addr=0x12)]
    with pytest.raises(RegisterNotInHeaderError):
        FrameParser(layout, specs).decode(FRAME)
