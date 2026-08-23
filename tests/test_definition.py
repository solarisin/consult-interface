from __future__ import annotations

import pytest

from consult_interface.definition import ConsultDefinition, ParamID


@pytest.fixture(scope="module")
def definition() -> ConsultDefinition:
    return ConsultDefinition()


def test_every_param_id_has_exactly_one_row(definition):
    table = definition.get_parameter_dict()
    assert set(table) == set(ParamID)


def test_param_count(definition):
    assert len(definition.get_parameter_dict()) == 59


def test_engine_speed_hr_ported_verbatim(definition):
    p = definition.get_parameter(ParamID.ENGINE_SPEED_HR)
    assert p.name == "Engine Speed HR"
    assert p.get_registers() == bytes([0x00, 0x01])
    assert p.get_register() == 0x01
    assert p.scale == 12.5
    assert p.unit_label == "RPM"


def test_coolant_temp_offset_ported_verbatim(definition):
    p = definition.get_parameter(ParamID.COOLANT_TEMP)
    assert p.get_register() == 0x08
    assert p.offset == -50
    assert p.scale == 1


def test_bit_param_ported_verbatim(definition):
    p = definition.get_parameter(ParamID.AC_ON)
    assert p.get_register() == 0x13
    assert p.bit == 4


def test_disputed_rows_are_recorded(definition):
    for pid in (ParamID.VEHICLE_SPEED, ParamID.BATTERY_VOLTAGE, ParamID.TPS):
        assert definition.disputed_note(pid), f"{pid.name} should carry a disputed note"


def test_undisputed_row_has_no_note(definition):
    assert definition.disputed_note(ParamID.COOLANT_TEMP) is None


def test_register_lookup_is_last_wins_for_bit_registers(definition):
    # PRESERVED QUIRK: register 0x13 hosts five bit params but the reverse map
    # keeps only the last one inserted. See the plan's Preserved Quirks section.
    assert definition.get_param_id_from_register(0x13) is ParamID.CLSD_THL_POS
    assert definition.get_param_id_from_register(0x21) is ParamID.RH_BANK_LEAN
