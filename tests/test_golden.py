"""The behavioural contract: decoded output must never change.

This test is rewired to the new API in Task 6, but the JSON data file it
reads is frozen at Task 1 and must never be regenerated.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import consult_interface.utils as u

GOLDEN = Path(__file__).parent / "golden" / "test_1_decoded.json"


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads(GOLDEN.read_text())


def test_golden_decode_matches(golden, project_root_path):
    command = bytes.fromhex(golden["command"].replace(" ", ""))
    params = u.command_to_params(command)
    for p in params:
        p.enable()

    capture = Path(project_root_path) / golden["capture"]
    with capture.open("rb") as f:
        header = bytearray()
        while byte := f.read(1):
            if byte == b"\xFF":
                f.seek(-1, 1)
                break
            header.append(byte[0])

        assert bytes(header).hex(" ").upper() == golden["header"]

        frame_size = f.read(2)[1] + 2
        f.seek(-2, 1)
        assert frame_size == golden["frame_size"]

        digest = hashlib.sha256()
        count = 0
        while frame := f.read(frame_size):
            if len(frame) != frame_size:
                break
            count += 1
            row = {}
            for p in params:
                p.update_value(bytes(header), frame)
                row[p.name] = p.get_value()
            digest.update(json.dumps(row, sort_keys=True).encode())

            expected = golden["sample"].get(str(count))
            if expected is not None:
                assert row == expected, f"frame {count} diverged"

    assert count == golden["frame_count"]
    assert digest.hexdigest() == golden["sha256"]
