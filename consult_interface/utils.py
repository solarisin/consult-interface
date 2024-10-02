from .definition import ConsultDefinition, ParamID
from .params import EcuParam, EcuParamSingle

Definition = ConsultDefinition()


def param_ids_to_param(param_ids: iter(ParamID)) -> list[EcuParam]:
    params = []
    for param_id in param_ids:
        try:
            param = Definition.get_parameter(param_id)
            params.append(param)
        except Exception as e:
            print(f'Exception converting parameter ID {param_id} to parameter: {e}')
            raise e
    return params


def param_id_of_single_param(param: EcuParamSingle) -> ParamID:
    return Definition.get_param_id_from_register(param.get_register())


def params_to_command(param_ids) -> bytes:
    cmd_bytes = bytearray()
    for param in param_ids_to_param(param_ids):
        try:
            cmd_bytes.append(Definition.cmd_register_param)
            cmd_bytes.append(param.get_register())
        except Exception as e:
            print(f'Exception converting parameter {param.name} to command: {e}')
            raise e
    cmd_bytes.append(Definition.start_stream)
    return cmd_bytes


def command_to_params(command: bytes) -> list[EcuParam]:
    params = []
    for i in range(0, len(command)):
        if command[i] == Definition.cmd_register_param:
            continue
        if command[i] == Definition.start_stream:
            break
        try:
            cmd_byte = command[i]
            param = Definition.get_parameter_from_register(command[i])
            params.append(param)
        except Exception as e:
            print(f'Exception converting command byte {command[i]} to parameter: {e}')
            raise e
    return params


def scan_match(buf: bytes, match: bytes) -> (bool, bytearray):
    """
    Search for bytes in match within the bytes in buf, returning the remaining bytes after the match if found
    :param buf: the bytes to search in
    :param match: the bytes to search for
    :return: a tuple containing a boolean indicating if the match was found and the remaining bytes after the match
    """
    # enforce that buf and match are both bytes or bytearrays
    if not isinstance(buf, bytes) and not isinstance(buf, bytearray):
        raise TypeError(f"buf must be bytes or bytearray, not {type(buf)}")
    if not isinstance(match, bytes) and not isinstance(match, bytearray):
        raise TypeError(f"match must be bytes or bytearray, not {type(match)}")

    match_len = len(match)
    if len(buf) < match_len:
        return False, buf
    for idx in range(len(buf) - (match_len - 1)):
        sub = buf[idx:idx + match_len]
        if sub == match:
            return True, buf[idx + match_len:]
    return False, bytearray()


def invert_byte(byte: bytes | bytearray | int) -> bytearray:
    if isinstance(byte, int):
        return bytearray([(~byte & 0xFF)])
    return bytearray([(~byte[0] & 0xFF)])


def invert_bytes(data: bytes | bytearray) -> bytearray:
    return bytearray([(~b & 0xFF) for b in data])


def bytes_to_str(b: bytes, binary=False):
    if binary:
        return ' '.join(f'{b[i]:08b}' for i in range(len(b)))
    b_str = b.hex().upper()
    return ' '.join(b_str[i:i + 2] for i in range(0, len(b_str), 2))
