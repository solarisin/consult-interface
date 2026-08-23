"""The behavioural contract: decoded output must never change.

The JSON data file this reads was frozen before the refactor began and must
never be regenerated -- a diff means behaviour changed, which is a bug.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from consult_interface.definition import ConsultDefinition
from consult_interface.frames import FrameLayout, FrameParser

GOLDEN = Path(__file__).parent / "golden" / "test_1_decoded.json"


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads(GOLDEN.read_text())


def test_golden_decode_matches(golden, project_root_path):
    definition = ConsultDefinition()
    command = bytes.fromhex(golden["command"].replace(" ", ""))

    # Rebuild the selection exactly as the original command_to_params did:
    # skip 0x5A markers, stop at 0xF0, resolve each register through the
    # last-wins reverse map.
    specs = []
    for byte in command:
        if byte == definition.cmd_register_param:
            continue
        if byte == definition.start_stream:
            break
        spec = definition.get_parameter_from_register(byte)
        assert spec is not None, f"register 0x{byte:02X} did not resolve"
        specs.append(spec)
    assert len(specs) == 14

    capture = Path(project_root_path) / golden["capture"]
    with capture.open("rb") as f:
        header = bytearray()
        while byte_ := f.read(1):
            if byte_ == b"\xff":
                f.seek(-1, 1)
                break
            header.append(byte_[0])

        assert bytes(header).hex(" ").upper() == golden["header"]

        frame_size = f.read(2)[1] + 2
        f.seek(-2, 1)
        assert frame_size == golden["frame_size"]

        layout = FrameLayout.from_header(bytes(header))
        parser = FrameParser(layout, specs)
        by_name = {spec.param_id: spec.name for spec in specs}

        digest = hashlib.sha256()
        count = 0
        while frame := f.read(frame_size):
            if len(frame) != frame_size:
                break
            count += 1
            decoded = parser.decode(frame)
            row = {by_name[pid]: value for pid, value in decoded.items()}
            digest.update(json.dumps(row, sort_keys=True).encode())

            expected = golden["sample"].get(str(count))
            if expected is not None:
                assert row == expected, f"frame {count} diverged"

    assert count == golden["frame_count"]
    assert digest.hexdigest() == golden["sha256"]
