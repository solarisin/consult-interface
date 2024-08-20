import consult_interface as ci


def test_scan_match():
    register_byte = b'\x5A'
    register_byte2 = ci.Definition.msg_register_param.to_bytes(1, 'big')
    assert register_byte == register_byte2

    inputs = [
        (b'\xFF\xFF\xFF\xEF\x5A', ci.Definition.init),
        (b'\xFF\xFF\xFF\xEF', ci.Definition.init),
        (b'\xFF\xFF\xEF', ci.Definition.init),
        (b'\xFF\xEF', ci.Definition.init),
        (b'\xFF\x5A\x03\x5A', ci.Definition.msg_register_param.to_bytes(1, 'little'))
    ]
    # ([found], [remaining bytes])
    results = [
        (True, b'\x5A'),
        (True, b''),
        (True, b''),
        (False, b'\xFF\xEF'),
        (True, b'\x03\x5A')
    ]

    assert len(inputs) == len(results)
    for i in range(len(inputs)):
        # logging.warning(f"Testing scan_match with input: {inputs[i]}")
        # TODO figure out why logging doesn't work in tests
        # input_buf, input_match = inputs[i]
        # result_found, result_remaining = results[i]
        # print(f"Testing scan_match with input: ('{input_buf.hex(' ').upper()}', '{input_match.hex(' ').upper()}') - expecting ({result_found}, '{result_remaining.hex(' ').upper()}')")
        assert ci.utils.scan_match(inputs[i][0], inputs[i][1]) == results[i]
