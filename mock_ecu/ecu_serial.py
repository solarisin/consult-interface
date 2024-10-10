import json

class Behavior:
    def __init__(self, name: str, type: str):
        self.name = name
        self.type = type

class CommandBehavior(Behavior):
    def __init__(self, name: str, match: dict, response: dict):
        super().__init__(name, "command")
        self.match = match
        self.response = response

def bytes_to_str(b: bytes, binary=False):
    if binary:
        return ' '.join(f'{b[i]:08b}' for i in range(len(b)))
    b_str = b.hex().upper()
    return ' '.join(b_str[i:i + 2] for i in range(0, len(b_str), 2))

def parse_hex_str_array(hex_str_array: list[str]) -> bytes:
    return bytes([int(x, 16) for x in hex_str_array])

def start():
    print("Starting mock ECU...\n")
    with open("behaviors.json", "r") as f:
        j = json.load(f)
        serial_config = j["serial_config"]
        behaviors = j["behaviors"]

    for b in behaviors:
        header = f"------- Behavior: {b['name']} -------"
        print(header)
        if b["type"] == "command":
            if b['match']['type'] == 'hex':
                print(f"Match: {bytes_to_str(parse_hex_str_array(b['match']['value']))}")
            if b['response']:
                if b['response']['type'] == 'hex':
                    response_bytes = parse_hex_str_array(b['response']['value'])
                    print(f"Response: {bytes_to_str(response_bytes)}")
            else:
                print(f"Response: None")
        elif b["type"] == "stream":
            print(f"Match start: {bytes_to_str(parse_hex_str_array(b['match_start']['value']))}")
            print(f"Match stop: {bytes_to_str(parse_hex_str_array(b['match_stop']['value']))}")
            print(f"Stream file: {b['file']}")
            print(f"Block length: {b['block_length']}")
            print(f"Interval: {b['interval']}")
        else:
            print(f"Invalid behavior type: {b['type']}")
        print()

start()