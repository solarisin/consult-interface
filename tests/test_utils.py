import logging

import consult_interface as ci
from consult_interface.params import EcuParamBit


def test_invert_bytes():
    assert ci.utils.invert_bytes(b"\x01") == b"\xfe"
    assert ci.utils.invert_bytes(b"\x00") == b"\xff"
    assert ci.utils.invert_bytes(b"\xff") == b"\x00"
    assert ci.utils.invert_bytes(b"\xfe") == b"\x01"
    assert ci.utils.invert_bytes(b"\x01\x02\x03\x04\x05") == b"\xfe\xfd\xfc\xfb\xfa"


def test_param_id_of_single_param():
    for param_id, param in ci.Definition.get_parameter_dict().items():
        if not isinstance(param, ci.params.EcuParamSingle):
            continue
        assert param_id == ci.utils.param_id_of_single_param(param)


def test_command_to_params():
    params = ci.utils.command_to_params(b"\x5a\x01\xf0")
    assert len(params) == 1
    assert params[0].name == "Engine Speed HR"
    assert params[0].get_register() == 0x01


def test_scan_match():
    register_byte = bytes([ci.Definition.cmd_register_param])
    register_byte2 = ci.Definition.cmd_register_param.to_bytes(1, "big")
    assert register_byte == register_byte2

    inputs = [
        (b"\xff\xff\xff\xef\x5a", bytes(ci.Definition.init)),
        (b"\xff\xff\xff\xef", bytes(ci.Definition.init)),
        (b"\xff\xff\xef", bytes(ci.Definition.init)),
        (b"\xff\xef", bytes(ci.Definition.init)),
        (b"\xff\x5a\x03\x5a", bytes([ci.Definition.cmd_register_param])),
    ]
    # ([found], [remaining bytes])
    results = [(True, b"\x5a"), (True, b""), (True, b""), (False, b"\xff\xef"), (True, b"\x03\x5a")]

    assert len(inputs) == len(results)
    for i in range(len(inputs)):
        # logging.warning(f"Testing scan_match with input: {inputs[i]}")
        # TODO figure out why logging doesn't work in tests
        # input_buf, input_match = inputs[i]
        # result_found, result_remaining = results[i]
        # print(f"Testing scan_match with input: ('{input_buf.hex(' ').upper()}', '{input_match.hex(' ').upper()}') - expecting ({result_found}, '{result_remaining.hex(' ').upper()}')")
        assert ci.utils.scan_match(inputs[i][0], inputs[i][1]) == results[i]
