"""One-shot generator for the golden decode contract.

Run against the PRE-REFACTOR code to capture current behaviour:

    MPLBACKEND=Agg uv run python tests/golden/generate_golden.py

The emitted JSON is a frozen contract. Never regenerate it to make a
failing test pass -- a diff means behaviour changed, which is a bug.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import consult_interface.utils as u

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPTURE = REPO_ROOT / "docs" / "test_data.hex"
OUT = REPO_ROOT / "tests" / "golden" / "test_1_decoded.json"

COMMAND = (
    b"\x5A\x0B\x5A\x01\x5A\x08\x5A\x0C\x5A\x0D\x5A\x03\x5A\x05"
    b"\x5A\x09\x5A\x13\x5A\x16\x5A\x17\x5A\x1A\x5A\x1C\x5A\x21\xF0"
)


def decode_all() -> dict:
    params = u.command_to_params(COMMAND)
    for p in params:
        p.enable()

    with CAPTURE.open("rb") as f:
        header = bytearray()
        while byte := f.read(1):
            if byte == b"\xFF":
                f.seek(-1, 1)
                break
            header.append(byte[0])

        frame_size = f.read(2)[1] + 2
        f.seek(-2, 1)

        digest = hashlib.sha256()
        rows: dict[int, dict[str, float]] = {}
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
            rows[count] = row

    keep = set(range(1, 11)) | set(range(count - 9, count + 1))
    keep |= {n for n in rows if n % 500 == 0}
    sample = {str(n): rows[n] for n in sorted(keep) if n in rows}

    return {
        "schema": 1,
        "capture": "docs/test_data.hex",
        "command": COMMAND.hex(" ").upper(),
        "header": bytes(header).hex(" ").upper(),
        "frame_size": frame_size,
        "frame_count": count,
        "sha256": digest.hexdigest(),
        "sample": sample,
    }


if __name__ == "__main__":
    data = decode_all()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"frames={data['frame_count']} sha256={data['sha256']}")
