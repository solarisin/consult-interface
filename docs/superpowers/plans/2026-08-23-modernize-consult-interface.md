# Consult-Interface Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retarget consult-interface to Python 3.12+ and restructure it from mutable global parameter state into immutable, fully-typed, TOML-backed components — without changing a single decoded value.

**Architecture:** A golden-output test is captured from the current code FIRST and becomes the contract every later task must satisfy. The parameter table moves from 60 lines of imperative Python into `params.toml`. Mutable `EcuParam` objects split into frozen `ParamSpec` descriptors plus a `FrameParser` that returns values instead of mutating shared state. `ci_serial.py` splits into a `Transport` Protocol (byte movement) and a `ConsultSession` (protocol logic).

**Tech Stack:** Python 3.12+, uv, hatchling, tomllib (stdlib), pyserial, click, pytest, ruff, mypy

**Spec:** `docs/superpowers/specs/2026-08-23-modernize-consult-interface-design.md`

## Global Constraints

- **Decoded output must not change.** Every task must leave `pytest tests/test_golden.py` passing. If clean and identical ever conflict, identical wins — stop and raise it rather than changing a value.
- Python floor is `>=3.12`. CI matrix is 3.12 and 3.13.
- `concept/` and `mock_ecu/` are excluded from ruff, mypy, and all refactoring. Do not touch them.
- `docs/params.csv` is reference material only. It is never loaded at runtime.
- Package version becomes `0.2.0`. No deprecation shims — the API breaks cleanly.
- Commit after every task. Never squash tasks together.
- Run tests with `MPLBACKEND=Agg` until Task 9 removes the plotting code.

## Preserved Quirks (deliberate — do not "fix" these)

These are current behaviour. The golden test enforces them. Each is recorded, not repaired:

1. **`DualParam` substitutes `0`** for a missing MSB or LSB, raising `RegisterNotInHeaderError` only when both are absent.
2. **`BitParam` returns the raw bit**, bypassing scale and offset entirely.
3. **Frame sanity-check failures log an error and continue**, they do not raise.
4. **Register→param lookup is last-wins.** `_register_to_param_id_dict[p.get_register()] = pid` overwrites, so bit register `0x13` resolves ONLY to `CLSD_THL_POS` and `0x21` resolves ONLY to `RH_BANK_LEAN`. Five bit params (`AC_ON`, `POWER_STEERING`, `PARK_NEUTRAL`, `CRANKING`, `LH_BANK_LEAN`) are unreachable through `get_parameter_from_register`. This is almost certainly a latent bug, but fixing it would decode extra parameters and break the golden contract. Preserve it and record it.

## File Structure

| File | Responsibility |
|---|---|
| `src/consult_interface/definition.py` | `ParamID` enum; `ConsultDefinition` registry loading `params.toml`; lookups |
| `src/consult_interface/params.py` | Frozen `ParamSpec` / `SingleParam` / `DualParam` / `BitParam` descriptors |
| `src/consult_interface/params.toml` | The parameter data table |
| `src/consult_interface/frames.py` | Byte helpers, `FrameLayout`, `FrameParser`, `RegisterNotInHeaderError` |
| `src/consult_interface/transport.py` | `Transport` Protocol, `SerialTransport`, `CaptureTransport`, `ReadParamFramesThread` |
| `src/consult_interface/session.py` | `ConsultSession`: init handshake, register select, stream, stop |
| `src/consult_interface/__init__.py` | Public API re-exports |
| `tests/golden/test_1_decoded.json` | The behavioural contract (data — never regenerate after Task 1) |
| `tests/test_golden.py` | Asserts the contract |
| `tests/test_definition.py` | TOML loading and validation |
| `tests/test_frames.py` | Layout parsing and decode semantics |
| `tests/test_transport.py` | Capture replay and handshake |

**Deleted by the end:** `consult_interface/utils.py`, `consult_interface/ci_serial.py`, `tests/test_utils.py`, `tests/test_params.py`, `tests/test_frame.py`.

---

### Task 1: Capture the golden-output contract

This runs against the CURRENT unmodified code. Nothing is refactored yet. The output of this task is the contract every later task must satisfy.

**Files:**
- Create: `tests/golden/generate_golden.py`
- Create: `tests/golden/test_1_decoded.json`
- Create: `tests/test_golden.py`

**Interfaces:**
- Consumes: current `consult_interface.utils.command_to_params`, `EcuParam.update_value`, `EcuParam.get_value`
- Produces: `tests/golden/test_1_decoded.json` with keys `schema`, `capture`, `command`, `header`, `frame_size`, `frame_count`, `sha256`, `sample`

- [ ] **Step 1: Write the generator**

Create `tests/golden/generate_golden.py`:

```python
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

from consult_interface import Definition
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
```

- [ ] **Step 2: Run the generator**

Run: `MPLBACKEND=Agg uv run python tests/golden/generate_golden.py`

Expected output (these values are verified against the current code — if they differ, STOP and investigate before continuing):

```
frames=39147 sha256=8ed1a4d17859b50b34fb0e5a1bfc29e2a5c1d2efdd8d339d25cd5d80061924eb
```

- [ ] **Step 3: Sanity-check the captured values**

Run: `uv run python -c "import json;d=json.load(open('tests/golden/test_1_decoded.json'));print(json.dumps(d['sample']['1'],indent=2))"`

Expected — frame 1 must look like a real idling engine:

```
"Engine Speed HR": 700.0,
"Coolant Temp": 77,
"Vehicle Speed": 0,
"CLSD/THL POS": 1
```

If Engine Speed is not near 700 or Coolant Temp is not near 77, the capture is being read wrong. Stop.

- [ ] **Step 4: Write the contract test**

Create `tests/test_golden.py`:

```python
"""The behavioural contract: decoded output must never change.

This test is rewired to the new API in Task 6, but the JSON data file it
reads is frozen at Task 1 and must never be regenerated.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from consult_interface import Definition
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
```

- [ ] **Step 5: Run the contract test to verify it passes**

Run: `MPLBACKEND=Agg uv run pytest tests/test_golden.py -v`
Expected: PASS

- [ ] **Step 6: Prove the test actually catches drift**

Temporarily edit `consult_interface/definition.py` and change the `COOLANT_TEMP` offset from `-50` to `-49`.

Run: `MPLBACKEND=Agg uv run pytest tests/test_golden.py -v`
Expected: FAIL with "frame 1 diverged"

Revert the edit and re-run. Expected: PASS.

A safety net you have not seen fail is not a safety net.

- [ ] **Step 7: Commit**

```bash
git add tests/golden/ tests/test_golden.py
git commit -m "Capture golden decode contract before refactor

39147 frames from docs/test_data.hex decoded with the current code,
stored as a sampled table plus a SHA-256 over the full stream. Every
later refactor task must leave this passing."
```

---

### Task 2: Retarget to Python 3.12 and add tooling

**Files:**
- Modify: `pyproject.toml`
- Create: `.python-version`
- Modify: `.github/workflows/ci.yml`
- Modify: `docker/Dockerfile`

**Interfaces:**
- Consumes: nothing
- Produces: a 3.12 toolchain with ruff and mypy configured (mypy not yet enforced in CI — that lands in Task 10)

- [ ] **Step 1: Pin the interpreter**

```bash
echo "3.12" > .python-version
```

- [ ] **Step 2: Update pyproject.toml**

Replace the `[project]` block's `requires-python` and `dependencies`, and append tool config. The full result:

```toml
[project]
name = "consult-interface"
version = "0.2.0"
description = "Host-side implementation of the Nissan CONSULT diagnostic protocol"
authors = [{ name = "Rob L.", email = "solarisin@gmail.com" }]
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "pyserial>=3.5,<4.0",
    "click>=8.1.7,<9.0",
]

[project.scripts]
cli = "consult_interface.cli.cli:cli"

[dependency-groups]
dev = [
    "pytest>=8.3.2,<9.0",
    "pytest-html>=4.1.1,<5.0",
    "matplotlib>=3.9.2,<4.0",
    "ruff>=0.6",
    "mypy>=1.11",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["consult_interface"]

[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = ["concept", "mock_ecu"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["consult_interface"]
exclude = ["concept", "mock_ecu"]

[tool.pytest.ini_options]
testpaths = "tests"
log_cli = true
log_cli_level = "DEBUG"
log_cli_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_cli_date_format = "%Y-%m-%d %H:%M:%S.%f"
log_level = "DEBUG"
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_date_format = "%Y-%m-%d %H:%M:%S.%f"
```

Note what changed: `timer` dropped (unused), `matplotlib` moved to dev, version bumped to 0.2.0, description filled in.

- [ ] **Step 3: Re-lock and sync on 3.12**

Run: `uv lock && uv sync`
Expected: uv downloads `cpython-3.12.x` (the dev Pi's system Python is 3.11.2), then installs.

Verify: `uv run python -V` prints `Python 3.12.x`

- [ ] **Step 4: Confirm the contract still holds**

Run: `MPLBACKEND=Agg uv run pytest -v`
Expected: all tests PASS, including `test_golden.py`

- [ ] **Step 5: Update CI for the 3.12/3.13 matrix**

Replace `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
    - name: Check out the code
      uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v5
      with:
        enable-cache: true
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: uv sync --locked

    - name: Lint
      run: uv run ruff check .

    - name: Format check
      run: uv run ruff format --check .

    - name: Run tests
      run: uv run pytest
      env:
        MPLBACKEND: Agg
```

Mypy is deliberately absent here — it is added in Task 10 once the code actually passes strict mode.

- [ ] **Step 6: Update the Dockerfile base image**

In `docker/Dockerfile`, change the base image line so it matches the new floor:

```dockerfile
FROM python:3.12
```

- [ ] **Step 7: Format the existing code and check lint damage**

Run: `uv run ruff format . && uv run ruff check . --statistics`

Expected: formatting rewrites files; `ruff check` reports violations in `consult_interface/` (unused import, bare except, builtin shadowing). Do NOT fix them yet — later tasks delete or rewrite most of that code. Record the count for comparison.

- [ ] **Step 8: Confirm the contract survived formatting**

Run: `MPLBACKEND=Agg uv run pytest tests/test_golden.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock .python-version .github/workflows/ci.yml docker/Dockerfile consult_interface tests
git commit -m "Retarget to Python 3.12+ and add ruff/mypy config

requires-python >=3.12, CI matrix on 3.12 and 3.13, ruff formatting
applied. Drops the unused timer dependency and moves matplotlib to the
dev group. Mypy is configured but not yet enforced in CI."
```

---

### Task 3: Move to src/ layout

**Files:**
- Move: `consult_interface/` → `src/consult_interface/`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nothing
- Produces: importable `consult_interface` package from `src/`

- [ ] **Step 1: Move the package**

```bash
mkdir -p src
git mv consult_interface src/consult_interface
```

- [ ] **Step 2: Point hatchling and mypy at the new location**

In `pyproject.toml`, change two blocks:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/consult_interface"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src/consult_interface"]
exclude = ["concept", "mock_ecu"]
```

- [ ] **Step 3: Re-sync so the editable install picks up the new path**

Run: `uv sync --reinstall-package consult-interface`

Verify: `uv run python -c "import consult_interface, pathlib; print(pathlib.Path(consult_interface.__file__).parent)"`
Expected: a path ending in `src/consult_interface`

- [ ] **Step 4: Confirm the contract still holds**

Run: `MPLBACKEND=Agg uv run pytest -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Move package to src/ layout"
```

---

### Task 4: Extract the parameter table to params.toml

The table's *values* port verbatim. This task changes where the table lives, not what it says. The `EcuParam` classes are untouched — they get replaced in Task 6.

**Files:**
- Create: `src/consult_interface/params.toml`
- Create: `tests/golden/generate_params_toml.py` (throwaway generator, deleted in this task)
- Modify: `src/consult_interface/definition.py`
- Create: `tests/test_definition.py`

**Interfaces:**
- Consumes: `ParamID` from `definition.py`
- Produces: `params.toml` with `schema_version = 1` and a `[[param]]` array; `ConsultDefinition` loading it

- [ ] **Step 1: Write the throwaway generator**

Create `tests/golden/generate_params_toml.py`:

```python
"""One-shot: emit params.toml from the current hardcoded table, then delete me."""

from __future__ import annotations

from pathlib import Path

from consult_interface import Definition
from consult_interface.params import EcuParamBit, EcuParamDual, EcuParamSingle

OUT = Path(__file__).resolve().parents[2] / "src" / "consult_interface" / "params.toml"

DISPUTED = {
    "VEHICLE_SPEED": "params.csv says Value * 2 (kph); km/h vs kph is cosmetic",
    "BATTERY_VOLTAGE": "params.csv says Value * 80 (mV); the V label is likely wrong",
    "TPS": "params.csv says Value * 20 (mV); code labels it % -- genuine conflict",
}


def render(pid, p) -> str:
    lines = ["[[param]]", f'id = "{pid.name}"']
    if isinstance(p, EcuParamDual):
        lines.append('kind = "dual"')
        lines.append(f'name = "{p.name}"')
        lines.append(f"register_msb = 0x{p.register_msb:02X}")
        lines.append(f"register_lsb = 0x{p.register_lsb:02X}")
    elif isinstance(p, EcuParamBit):
        lines.append('kind = "bit"')
        lines.append(f'name = "{p.name}"')
        lines.append(f"register = 0x{p.register:02X}")
        lines.append(f"bit = {p.bit}")
    elif isinstance(p, EcuParamSingle):
        lines.append('kind = "single"')
        lines.append(f'name = "{p.name}"')
        lines.append(f"register = 0x{p.register:02X}")
    else:
        raise TypeError(f"unknown param type {type(p)}")

    if not isinstance(p, EcuParamBit):
        if p.unit_label:
            lines.append(f'unit = "{p.unit_label}"')
        if p.scale != 1:
            lines.append(f"scale = {p.scale!r}")
        if p.offset != 0:
            lines.append(f"offset = {p.offset!r}")

    if pid.name in DISPUTED:
        lines.append(f'disputed = "{DISPUTED[pid.name]}"')
    return "\n".join(lines)


if __name__ == "__main__":
    blocks = [render(pid, p) for pid, p in Definition.get_parameter_dict().items()]
    body = "\n\n".join(blocks)
    OUT.write_text(
        "# Nissan CONSULT ECU parameter table.\n"
        "#\n"
        "# Generated once from the original hardcoded table. Values are authoritative\n"
        "# here now -- docs/params.csv is human reference material and is NOT loaded.\n"
        "# Rows carrying `disputed` conflict with params.csv and are deliberately\n"
        "# left at the code's original value pending confirmation on a real ECU.\n\n"
        "schema_version = 1\n\n" + body + "\n"
    )
    print(f"wrote {len(blocks)} params to {OUT}")
```

- [ ] **Step 2: Generate the table**

Run: `MPLBACKEND=Agg uv run python tests/golden/generate_params_toml.py`
Expected: `wrote 59 params to .../src/consult_interface/params.toml`

- [ ] **Step 3: Eyeball the output**

Run: `head -40 src/consult_interface/params.toml`

Expected to contain, among others:

```toml
[[param]]
id = "ENGINE_SPEED_HR"
kind = "dual"
name = "Engine Speed HR"
register_msb = 0x00
register_lsb = 0x01
unit = "RPM"
scale = 12.5
```

Verify `BATTERY_VOLTAGE` carries its `disputed` line.

- [ ] **Step 4: Write the failing test for the loader**

Create `tests/test_definition.py`:

```python
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
```

- [ ] **Step 5: Run to verify it fails**

Run: `MPLBACKEND=Agg uv run pytest tests/test_definition.py -v`
Expected: FAIL — `ConsultDefinition` does not accept construction from TOML yet and has no `disputed_note`

- [ ] **Step 6: Rewrite ConsultDefinition to load the TOML**

In `src/consult_interface/definition.py`, keep the `ParamID` enum exactly as it is and replace the whole `ConsultDefinition` class body with:

```python
import tomllib
from pathlib import Path

from .params import EcuParam, EcuParamBit, EcuParamDual, EcuParamSingle

TABLE_PATH = Path(__file__).with_name("params.toml")


class ParamTableError(ValueError):
    """Raised when params.toml is malformed or disagrees with ParamID."""


class ConsultDefinition:
    def __init__(self, table_path: Path | None = None) -> None:
        self.init = [0xFF, 0xFF, 0xEF]
        self.cmd_ecu_part_number = 0xD0
        self.cmd_register_param = 0x5A
        self.start_stream = 0xF0
        self.stop_stream = 0x30

        self._parameters: dict[ParamID, EcuParam] = {}
        self._disputed: dict[ParamID, str] = {}
        self._load(table_path or TABLE_PATH)
        self._validate()

        self._register_to_param_id_dict: dict[int, ParamID] = {}
        for pid, p in self._parameters.items():
            # Last-wins, deliberately: preserves the original reverse-map behaviour
            # where several bit params share one register.
            self._register_to_param_id_dict[p.get_register()] = pid

    def _load(self, path: Path) -> None:
        raw = tomllib.loads(path.read_text())
        if raw.get("schema_version") != 1:
            raise ParamTableError(f"unsupported schema_version: {raw.get('schema_version')!r}")

        for row in raw.get("param", []):
            try:
                pid = ParamID[row["id"]]
            except KeyError as exc:
                raise ParamTableError(f"unknown ParamID: {row.get('id')!r}") from exc
            if pid in self._parameters:
                raise ParamTableError(f"duplicate row for {pid.name}")

            kind = row.get("kind")
            name = row["name"]
            unit = row.get("unit", "")
            scale = row.get("scale", 1)
            offset = row.get("offset", 0)

            if kind == "single":
                param: EcuParam = EcuParamSingle(pid, name, row["register"], unit, scale, offset)
            elif kind == "dual":
                param = EcuParamDual(
                    pid, name, row["register_msb"], row["register_lsb"], unit, scale, offset
                )
            elif kind == "bit":
                bit = row["bit"]
                if not 0 <= bit <= 7:
                    raise ParamTableError(f"{pid.name}: bit {bit} out of range 0-7")
                param = EcuParamBit(pid, name, row["register"], bit)
            else:
                raise ParamTableError(f"{pid.name}: unknown kind {kind!r}")

            for reg in param.get_registers():
                if not 0x00 <= reg <= 0xFF:
                    raise ParamTableError(f"{pid.name}: register 0x{reg:X} out of range")

            self._parameters[pid] = param
            if note := row.get("disputed"):
                self._disputed[pid] = note

    def _validate(self) -> None:
        missing = set(ParamID) - set(self._parameters)
        if missing:
            raise ParamTableError(
                "params.toml is missing rows for: "
                + ", ".join(sorted(m.name for m in missing))
            )

        seen: set[tuple[bytes, int | None]] = set()
        for p in self._parameters.values():
            key = (p.get_registers(), p.bit if isinstance(p, EcuParamBit) else None)
            if key in seen:
                raise ParamTableError(f"duplicate register/bit combination: {p.name}")
            seen.add(key)

    def disputed_note(self, pid: ParamID) -> str | None:
        """Return the params.csv conflict note for this param, if any."""
        return self._disputed.get(pid)
```

Keep every existing accessor (`get_param_id_from_register`, `get_parameter_from_register`, `get_parameter_from_param_id`, `get_parameter`, `get_parameter_list`, `get_parameter_dict`, `get_enabled_parameters`, `count_enabled_parameters`) exactly as written — they are unchanged.

- [ ] **Step 7: Run the definition tests**

Run: `MPLBACKEND=Agg uv run pytest tests/test_definition.py -v`
Expected: PASS

- [ ] **Step 8: Confirm the contract still holds**

Run: `MPLBACKEND=Agg uv run pytest -v`
Expected: all PASS, `test_golden.py` included. If golden fails here, a value was mistranscribed into the TOML — diff the table against git history rather than regenerating the golden file.

- [ ] **Step 9: Delete the throwaway generator and commit**

```bash
rm tests/golden/generate_params_toml.py
git add -A
git commit -m "Move parameter table into params.toml

59 params generated verbatim from the hardcoded table and loaded with
tomllib. Adds validation (ParamID bijection, register range, duplicate
register/bit) and records the three params.csv conflicts as disputed
rows. Decoded output is unchanged."
```

---

### Task 5: Add frames.py with FrameLayout

New module, unit-tested, no consumers yet. Nothing is deleted in this task.

**Files:**
- Create: `src/consult_interface/frames.py`
- Create: `tests/test_frames.py`

**Interfaces:**
- Consumes: nothing
- Produces: `invert_byte`, `invert_bytes`, `bytes_to_str`, `RegisterNotInHeaderError`, `FrameLayout` with `.registers: tuple[int, ...]`, `.from_header(header: bytes) -> FrameLayout`, `.index_of(register: int) -> int`, `.__len__`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_frames.py`:

```python
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
    assert invert_byte(b"\x5A") == bytearray([0xA5])


def test_invert_bytes_round_trips():
    data = b"\xFF\xFF\xEF"
    assert invert_bytes(invert_bytes(data)) == bytearray(data)


def test_invert_bytes_matches_init_handshake():
    assert invert_bytes(b"\xFF\xFF\xEF") == bytearray(b"\x00\x00\x10")


def test_bytes_to_str_hex():
    assert bytes_to_str(b"\x5A\x0B") == "5A 0B"


def test_bytes_to_str_binary():
    assert bytes_to_str(b"\x5A", binary=True) == "01011010"


def test_layout_recovers_register_order():
    layout = FrameLayout.from_header(HEADER)
    assert layout.registers == (
        0x0B, 0x01, 0x08, 0x0C, 0x0D, 0x03, 0x05,
        0x09, 0x13, 0x16, 0x17, 0x1A, 0x1C, 0x21,
    )


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
        FrameLayout.from_header(b"\xA5\x0B\xA5")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_frames.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'consult_interface.frames'`

- [ ] **Step 3: Write frames.py**

Create `src/consult_interface/frames.py`:

```python
"""Frame-level primitives for the CONSULT protocol.

The ECU echoes a register selection back with the 0x5A marker bytes inverted
to 0xA5 and the register bytes unchanged:

    A5 <reg> A5 <reg> ...

That echo IS the frame layout descriptor: data bytes in each subsequent
`FF <len> <data...>` frame appear in exactly the order the header lists.
"""

from __future__ import annotations

from dataclasses import dataclass

HEADER_MARKER = 0xA5
FRAME_START = 0xFF


class RegisterNotInHeaderError(ValueError):
    """A register was requested that the ECU's header echo does not list."""


def invert_byte(byte: bytes | bytearray | int) -> bytearray:
    """Bitwise-invert a single byte. The ECU acks commands with their inverse."""
    if isinstance(byte, int):
        return bytearray([~byte & 0xFF])
    return bytearray([~byte[0] & 0xFF])


def invert_bytes(data: bytes | bytearray) -> bytearray:
    """Bitwise-invert every byte in a sequence."""
    return bytearray((~b & 0xFF) for b in data)


def bytes_to_str(b: bytes, binary: bool = False) -> str:
    """Render bytes for logging: '5A 0B' by default, '01011010' if binary."""
    if binary:
        return " ".join(f"{byte:08b}" for byte in b)
    hex_str = b.hex().upper()
    return " ".join(hex_str[i : i + 2] for i in range(0, len(hex_str), 2))


@dataclass(frozen=True, slots=True)
class FrameLayout:
    """The ordered registers a frame's data bytes correspond to."""

    registers: tuple[int, ...]

    @classmethod
    def from_header(cls, header: bytes) -> FrameLayout:
        """Parse an `A5 <reg> A5 <reg> ...` echo into its register order."""
        if len(header) % 2 != 0:
            raise ValueError(
                f"header must be an even number of bytes, got {len(header)}: "
                f"{bytes_to_str(header)}"
            )
        return cls(tuple(header[1::2]))

    def index_of(self, register: int) -> int:
        """Position of `register` in the frame's data bytes."""
        try:
            return self.registers.index(register)
        except ValueError as exc:
            raise RegisterNotInHeaderError(
                f"register 0x{register:02X} not in header layout "
                f"{[f'0x{r:02X}' for r in self.registers]}"
            ) from exc

    def __len__(self) -> int:
        return len(self.registers)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_frames.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Confirm the contract still holds**

Run: `MPLBACKEND=Agg uv run pytest -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/consult_interface/frames.py tests/test_frames.py
git commit -m "Add frames.py with FrameLayout and byte helpers

Extracts the header[1::2] slice repeated across the codebase into a
named, tested FrameLayout type. No consumers yet."
```

---

### Task 6: Replace EcuParam with frozen ParamSpec and FrameParser

The core change. Mutable value-holding params become immutable descriptors; decoding returns a mapping.

**Files:**
- Rewrite: `src/consult_interface/params.py`
- Modify: `src/consult_interface/definition.py`
- Modify: `src/consult_interface/frames.py` (add `FrameParser`)
- Modify: `tests/test_frames.py`, `tests/test_definition.py`, `tests/test_golden.py`
- Delete: `tests/test_params.py`

**Interfaces:**
- Consumes: `FrameLayout`, `RegisterNotInHeaderError` from Task 5; `ConsultDefinition` from Task 4
- Produces: `ParamSpec` (frozen base), `SingleParam`, `DualParam`, `BitParam` each with `.param_id`, `.name`, `.unit`, `.scale`, `.offset`, `.registers -> tuple[int, ...]`, `.register -> int`, `.decode(layout, frame) -> float | int`; and `FrameParser(layout, specs).decode(frame) -> dict[ParamID, float | int]`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_frames.py`:

```python
from consult_interface.definition import ParamID
from consult_interface.frames import FrameParser
from consult_interface.params import BitParam, DualParam, SingleParam

# 14 data bytes matching HEADER's register order, prefixed with FF <len>.
FRAME = bytes([0xFF, 0x0E, 0x00, 0x38, 0x7F, 0xB2, 0x17, 0x6B, 0xD0,
               0x1C, 0x01, 0x68, 0x4C, 0x64, 0x76, 0x00])


def test_single_param_scales_and_offsets():
    spec = SingleParam(ParamID.COOLANT_TEMP, "Coolant Temp", 0x08, "C", 1, -50)
    layout = FrameLayout.from_header(HEADER)
    assert spec.decode(layout, FRAME) == 0x7F - 50


def test_dual_param_combines_msb_and_lsb():
    spec = DualParam(ParamID.ENGINE_SPEED_HR, "Engine Speed HR", 0x00, 0x01, "RPM", 12.5)
    layout = FrameLayout.from_header(HEADER)
    # 0x00 is absent from HEADER so the MSB substitutes 0; LSB 0x01 -> 0x38
    assert spec.decode(layout, FRAME) == 0x38 * 12.5


def test_dual_param_raises_only_when_both_registers_absent():
    spec = DualParam(ParamID.INJECTOR_TIME_RH, "Injector Time RH", 0x22, 0x23, "ms", 0.01)
    layout = FrameLayout.from_header(HEADER)
    with pytest.raises(RegisterNotInHeaderError):
        spec.decode(layout, FRAME)


def test_bit_param_returns_raw_bit_ignoring_scale():
    spec = BitParam(ParamID.CLSD_THL_POS, "CLSD/THL POS", 0x13, 0)
    layout = FrameLayout.from_header(HEADER)
    assert spec.decode(layout, FRAME) == (0x01 >> 0) & 1


def test_bit_param_reads_the_right_bit():
    spec = BitParam(ParamID.AC_ON, "A/C On", 0x13, 4)
    layout = FrameLayout.from_header(HEADER)
    assert spec.decode(layout, FRAME) == (0x01 >> 4) & 1


def test_single_param_raises_for_absent_register():
    spec = SingleParam(ParamID.EGT, "EGT", 0x12, "mV", 20)
    layout = FrameLayout.from_header(HEADER)
    with pytest.raises(RegisterNotInHeaderError):
        spec.decode(layout, FRAME)


def test_param_specs_are_frozen():
    spec = SingleParam(ParamID.COOLANT_TEMP, "Coolant Temp", 0x08, "C", 1, -50)
    with pytest.raises(Exception):
        spec.scale = 99


def test_frame_parser_decodes_all_specs():
    layout = FrameLayout.from_header(HEADER)
    specs = [
        SingleParam(ParamID.COOLANT_TEMP, "Coolant Temp", 0x08, "C", 1, -50),
        SingleParam(ParamID.VEHICLE_SPEED, "Vehicle Speed", 0x0B, "km/h", 2),
    ]
    result = FrameParser(layout, specs).decode(FRAME)
    assert result == {
        ParamID.COOLANT_TEMP: 0x7F - 50,
        ParamID.VEHICLE_SPEED: 0x00 * 2,
    }


def test_frame_parser_propagates_missing_register():
    layout = FrameLayout.from_header(HEADER)
    specs = [SingleParam(ParamID.EGT, "EGT", 0x12, "mV", 20)]
    with pytest.raises(RegisterNotInHeaderError):
        FrameParser(layout, specs).decode(FRAME)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_frames.py -v`
Expected: FAIL with `ImportError: cannot import name 'SingleParam'`

- [ ] **Step 3: Rewrite params.py**

Replace the entire contents of `src/consult_interface/params.py`:

```python
"""Immutable descriptions of ECU parameters.

A ParamSpec says what a register MEANS. It never holds a value -- decoding a
frame returns values (see frames.FrameParser) rather than mutating shared
state, which is what makes decode calls order-independent and thread-safe.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from .frames import FRAME_START, FrameLayout, RegisterNotInHeaderError

if TYPE_CHECKING:
    from .definition import ParamID

log = logging.getLogger(__name__)


def _data_bytes(frame: bytes, layout: FrameLayout) -> bytes:
    """Strip the `FF <len>` prefix, logging (not raising) on malformed frames.

    PRESERVED QUIRK: sanity failures log and continue, matching the original
    EcuParam.sanity_check.
    """
    if frame[0] != FRAME_START:
        log.error("Invalid frame start byte: %s", frame.hex(" "))
    if frame[1] != len(layout):
        log.error(
            "Frame declares %d data bytes but header lists %d registers: %s",
            frame[1],
            len(layout),
            frame.hex(" "),
        )
    return frame[2:]


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """Base description of one ECU parameter."""

    param_id: ParamID
    name: str
    unit: str = ""
    scale: float = 1.0
    offset: float = 0.0

    @property
    def registers(self) -> tuple[int, ...]:
        """Every register this parameter reads (MSB first for dual params)."""
        raise NotImplementedError

    @property
    def register(self) -> int:
        """The single register identifying this parameter (LSB for dual)."""
        raise NotImplementedError

    def decode(self, layout: FrameLayout, frame: bytes) -> float | int:
        """Read this parameter's value out of one frame."""
        raise NotImplementedError

    def _scaled(self, unscaled: int) -> float:
        return (unscaled * self.scale) + self.offset


@dataclass(frozen=True, slots=True)
class SingleParam(ParamSpec):
    """One register, scaled and offset."""

    register_addr: int = 0

    @property
    @override
    def registers(self) -> tuple[int, ...]:
        return (self.register_addr,)

    @property
    @override
    def register(self) -> int:
        return self.register_addr

    @override
    def decode(self, layout: FrameLayout, frame: bytes) -> float | int:
        data = _data_bytes(frame, layout)
        return self._scaled(data[layout.index_of(self.register_addr)])


@dataclass(frozen=True, slots=True)
class DualParam(ParamSpec):
    """Two registers combined as `msb << 8 | lsb`."""

    register_msb: int = 0
    register_lsb: int = 0

    @property
    @override
    def registers(self) -> tuple[int, ...]:
        return (self.register_msb, self.register_lsb)

    @property
    @override
    def register(self) -> int:
        return self.register_lsb

    @override
    def decode(self, layout: FrameLayout, frame: bytes) -> float | int:
        data = _data_bytes(frame, layout)

        # PRESERVED QUIRK: a missing half substitutes 0; only both missing raises.
        msb_found = lsb_found = True
        try:
            msb = data[layout.index_of(self.register_msb)]
        except RegisterNotInHeaderError:
            msb, msb_found = 0, False
        try:
            lsb = data[layout.index_of(self.register_lsb)]
        except RegisterNotInHeaderError:
            lsb, lsb_found = 0, False

        if not msb_found and not lsb_found:
            raise RegisterNotInHeaderError(
                f"neither register 0x{self.register_msb:02X} nor "
                f"0x{self.register_lsb:02X} is in the header layout"
            )
        return self._scaled((msb << 8) + lsb)


@dataclass(frozen=True, slots=True)
class BitParam(ParamSpec):
    """One bit of a status register."""

    register_addr: int = 0
    bit: int = 0

    @property
    @override
    def registers(self) -> tuple[int, ...]:
        return (self.register_addr,)

    @property
    @override
    def register(self) -> int:
        return self.register_addr

    @override
    def decode(self, layout: FrameLayout, frame: bytes) -> float | int:
        # PRESERVED QUIRK: returns the raw bit, ignoring scale and offset.
        data = _data_bytes(frame, layout)
        return (data[layout.index_of(self.register_addr)] >> self.bit) & 1
```

- [ ] **Step 4: Add FrameParser to frames.py**

Append to `src/consult_interface/frames.py`:

```python
if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .definition import ParamID
    from .params import ParamSpec


class FrameParser:
    """Decodes frames for a fixed layout and a fixed set of parameters."""

    def __init__(self, layout: FrameLayout, specs: Iterable[ParamSpec]) -> None:
        self._layout = layout
        self._specs = tuple(specs)

    @property
    def layout(self) -> FrameLayout:
        return self._layout

    @property
    def specs(self) -> tuple[ParamSpec, ...]:
        return self._specs

    def decode(self, frame: bytes) -> Mapping[ParamID, float | int]:
        """Decode one frame into `{ParamID: value}`.

        Raises RegisterNotInHeaderError if a spec's register is absent from the
        layout (for DualParam, only when both its registers are absent).
        """
        return {spec.param_id: spec.decode(self._layout, frame) for spec in self._specs}
```

Add `from typing import TYPE_CHECKING` to the module's imports.

- [ ] **Step 5: Point ConsultDefinition at the new spec classes**

In `src/consult_interface/definition.py`, change the import and the three construction branches in `_load`:

```python
from .params import BitParam, DualParam, ParamSpec, SingleParam
```

```python
            if kind == "single":
                param: ParamSpec = SingleParam(
                    param_id=pid, name=name, unit=unit, scale=scale,
                    offset=offset, register_addr=row["register"],
                )
            elif kind == "dual":
                param = DualParam(
                    param_id=pid, name=name, unit=unit, scale=scale, offset=offset,
                    register_msb=row["register_msb"], register_lsb=row["register_lsb"],
                )
            elif kind == "bit":
                bit = row["bit"]
                if not 0 <= bit <= 7:
                    raise ParamTableError(f"{pid.name}: bit {bit} out of range 0-7")
                param = BitParam(
                    param_id=pid, name=name, register_addr=row["register"], bit=bit,
                )
```

Then update the rest of the class for the new attribute names: `p.get_registers()` becomes `p.registers`, `p.get_register()` becomes `p.register`, `isinstance(p, EcuParamBit)` becomes `isinstance(p, BitParam)`. Delete `get_enabled_parameters` and `count_enabled_parameters` — there is no `enabled` flag any more. Rename `get_parameter_dict` / `get_parameter_list` / `get_parameter` / `get_param_id_from_register` / `get_parameter_from_register` are kept as-is.

In `_validate`, the duplicate key becomes:

```python
            key = (p.registers, p.bit if isinstance(p, BitParam) else None)
```

- [ ] **Step 6: Update test_definition.py for the new attribute names**

In `tests/test_definition.py`, replace the two accessor assertions:

```python
def test_engine_speed_hr_ported_verbatim(definition):
    p = definition.get_parameter(ParamID.ENGINE_SPEED_HR)
    assert p.name == "Engine Speed HR"
    assert p.registers == (0x00, 0x01)
    assert p.register == 0x01
    assert p.scale == 12.5
    assert p.unit == "RPM"


def test_coolant_temp_offset_ported_verbatim(definition):
    p = definition.get_parameter(ParamID.COOLANT_TEMP)
    assert p.register == 0x08
    assert p.offset == -50
    assert p.scale == 1


def test_bit_param_ported_verbatim(definition):
    p = definition.get_parameter(ParamID.AC_ON)
    assert p.register == 0x13
    assert p.bit == 4
```

- [ ] **Step 7: Rewire the golden test to the new API**

The JSON data file is NOT touched. Only the code that produces the rows changes. Replace the body of `tests/test_golden.py`:

```python
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
            if byte_ == b"\xFF":
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
```

- [ ] **Step 8: Delete the obsolete param test**

```bash
git rm tests/test_params.py
```

- [ ] **Step 9: Run the full suite**

Run: `MPLBACKEND=Agg uv run pytest -v`
Expected: PASS, including `test_golden.py`.

If the golden hash differs, a decode semantic changed. Diff the failing frame's row against `golden["sample"]` to find which parameter drifted. Do NOT regenerate the golden file.

`tests/test_frame.py` and `tests/test_utils.py` still reference the old API and will fail here. Fix them by deleting the now-dead assertions only if trivial; otherwise leave them failing and note it — Task 9 removes both files. If you leave them failing, this task's commit must say so.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "Replace mutable EcuParam with frozen ParamSpec and FrameParser

Params become immutable descriptors; decoding returns a mapping instead
of mutating shared objects, removing the ordering and thread-safety
hazards. The dual missing-half substitution, raw-bit return, and
log-and-continue sanity check are preserved deliberately and marked.
Golden contract unchanged."
```

---

### Task 7: Add transport.py

**Files:**
- Create: `src/consult_interface/transport.py`
- Create: `tests/test_transport.py`

**Interfaces:**
- Consumes: `invert_bytes` from `frames.py`
- Produces: `Transport` Protocol (`open()`, `close()`, `read(size: int) -> bytes`, `write(data: bytes) -> int | None`, `is_connected() -> bool`); `SerialTransport(port: str, baud: int = 9600)`; `CaptureTransport(path: Path)`; `ReadParamFramesThread(transport, frame_bytes, process_frame)`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_transport.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from consult_interface.transport import CaptureTransport, Transport


@pytest.fixture
def capture_path(project_root_path) -> Path:
    return Path(project_root_path) / "docs" / "test_data.hex"


def test_capture_transport_satisfies_the_protocol(capture_path):
    assert isinstance(CaptureTransport(capture_path), Transport)


def test_capture_transport_reads_requested_size(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    assert len(t.read(4)) == 4
    t.close()


def test_capture_transport_reads_sequentially(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    first, second = t.read(2), t.read(2)
    t.close()

    t2 = CaptureTransport(capture_path)
    t2.open()
    assert t2.read(4) == first + second
    t2.close()


def test_capture_transport_returns_short_read_at_eof(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    t.read(capture_path.stat().st_size - 2)
    assert len(t.read(100)) == 2
    t.close()


def test_capture_transport_writes_are_accepted_and_counted(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    assert t.write(b"\xFF\xFF\xEF") == 3
    t.close()


def test_capture_transport_records_what_was_written(capture_path):
    t = CaptureTransport(capture_path)
    t.open()
    t.write(b"\xFF\xFF\xEF")
    t.write(b"\x30")
    t.close()
    assert t.written == b"\xFF\xFF\xEF\x30"


def test_is_connected_tracks_open_and_close(capture_path):
    t = CaptureTransport(capture_path)
    assert not t.is_connected()
    t.open()
    assert t.is_connected()
    t.close()
    assert not t.is_connected()
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_transport.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'consult_interface.transport'`

- [ ] **Step 3: Write transport.py**

Create `src/consult_interface/transport.py`:

```python
"""Byte transport for the CONSULT protocol.

Transport moves bytes and knows nothing about the protocol. Protocol logic
lives in session.ConsultSession.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Protocol, runtime_checkable

import serial

log = logging.getLogger(__name__)

DEFAULT_BAUD = 9600


@runtime_checkable
class Transport(Protocol):
    """Anything that can move bytes to and from an ECU."""

    def open(self) -> None: ...

    def close(self) -> None: ...

    def read(self, size: int) -> bytes: ...

    def write(self, data: bytes) -> int | None: ...

    def is_connected(self) -> bool: ...


class SerialTransport:
    """Real 9600-baud serial connection over a USB adapter."""

    def __init__(self, port: str, baud: int = DEFAULT_BAUD) -> None:
        self._port = port
        self._baud = baud
        self._serial = serial.Serial(
            port, baud, timeout=None, xonxoff=False, rtscts=False, dsrdtr=False
        )

    def open(self) -> None:
        if not self._serial.is_open:
            self._serial.open()

    def close(self) -> None:
        self._serial.close()

    def read(self, size: int) -> bytes:
        return self._serial.read(size)

    def write(self, data: bytes) -> int | None:
        return self._serial.write(data)

    def is_connected(self) -> bool:
        return bool(self._serial.is_open)

    @property
    def raw(self) -> serial.Serial:
        """The underlying pyserial handle, for ReadParamFramesThread."""
        return self._serial


class CaptureTransport:
    """Replays a raw ECU capture file.

    Capture files start AFTER the command was sent and contain no init
    sequence, so writes are accepted, recorded, and otherwise ignored.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._handle: object | None = None
        self._written = bytearray()

    def open(self) -> None:
        if self._handle is None:
            self._handle = self._path.open("rb")

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def read(self, size: int) -> bytes:
        if self._handle is None:
            raise RuntimeError("CaptureTransport.read() before open()")
        return self._handle.read(size)

    def write(self, data: bytes) -> int | None:
        self._written.extend(data)
        return len(data)

    def is_connected(self) -> bool:
        return self._handle is not None

    @property
    def written(self) -> bytes:
        """Every byte written since construction, for assertions."""
        return bytes(self._written)


class ReadParamFramesThread(threading.Thread):
    """Pumps fixed-size frames off a transport into a callback."""

    def __init__(self, transport: Transport, frame_bytes: int, process_frame) -> None:
        super().__init__(daemon=True)
        self._transport = transport
        self._frame_size = frame_bytes
        self._running = False
        self.process_frame = process_frame

    def run(self) -> None:
        # BUGFIX: the original tested `if not self._port.open()`, but
        # Serial.open() returns None, so that branch always fired.
        opened_here = False
        if not self._transport.is_connected():
            self._transport.open()
            opened_here = True

        self._running = True
        try:
            while self._running:
                frame = self._transport.read(self._frame_size)
                if len(frame) == self._frame_size:
                    self.process_frame(frame)
        finally:
            if opened_here:
                self._transport.close()

    def stop(self) -> None:
        self._running = False
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_transport.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Confirm the contract still holds**

Run: `MPLBACKEND=Agg uv run pytest tests/test_golden.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/consult_interface/transport.py tests/test_transport.py
git commit -m "Add transport.py with Transport Protocol and CaptureTransport

Splits byte movement out of ci_serial.py. CaptureTransport promotes the
test-local MockConsultSerial into a supported replay transport. Fixes the
Serial.open() truthiness bug in the frame-reader thread."
```

---

### Task 8: Add session.py and delete the old modules

**Files:**
- Create: `src/consult_interface/session.py`
- Modify: `src/consult_interface/__init__.py`
- Delete: `src/consult_interface/ci_serial.py`, `src/consult_interface/utils.py`
- Modify: `tests/test_transport.py`

**Interfaces:**
- Consumes: `Transport` (Task 7), `FrameLayout` / `FrameParser` (Tasks 5-6), `ConsultDefinition` (Task 4)
- Produces: `InitializeFailedError`; `ConsultSession(transport, definition=None)` with `.initialize() -> bool`, `.select(param_ids: Iterable[ParamID]) -> FrameParser`, `.read_frame(parser) -> Mapping[ParamID, float | int]`, `.stop() -> None`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_transport.py`:

```python
from consult_interface.definition import ParamID
from consult_interface.session import ConsultSession, InitializeFailedError


class ScriptedTransport:
    """Transport returning canned responses, for handshake tests."""

    def __init__(self, responses: bytes) -> None:
        self._responses = responses
        self._pos = 0
        self.written = bytearray()
        self._open = False

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def read(self, size: int) -> bytes:
        chunk = self._responses[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    def write(self, data: bytes) -> int | None:
        self.written.extend(data)
        return len(data)

    def is_connected(self) -> bool:
        return self._open


def test_initialize_sends_handshake_and_accepts_inverted_reply():
    t = ScriptedTransport(b"\x00\x00\x10")
    assert ConsultSession(t).initialize() is True
    assert bytes(t.written) == b"\xFF\xFF\xEF"


def test_initialize_raises_on_wrong_reply():
    t = ScriptedTransport(b"\xDE\xAD\xBE")
    with pytest.raises(InitializeFailedError):
        ConsultSession(t).initialize()


def test_select_writes_register_command_terminated_by_start_stream():
    header = bytes.fromhex("A50BA508")
    t = ScriptedTransport(header)
    session = ConsultSession(t)
    session.select([ParamID.VEHICLE_SPEED, ParamID.COOLANT_TEMP])
    assert bytes(t.written) == b"\x5A\x0B\x5A\x08\xF0"


def test_select_returns_parser_matching_the_echoed_header():
    header = bytes.fromhex("A50BA508")
    session = ConsultSession(ScriptedTransport(header))
    parser = session.select([ParamID.VEHICLE_SPEED, ParamID.COOLANT_TEMP])
    assert parser.layout.registers == (0x0B, 0x08)


def test_stop_writes_stop_byte():
    t = ScriptedTransport(b"")
    ConsultSession(t).stop()
    assert bytes(t.written) == b"\x30"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_transport.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'consult_interface.session'`

- [ ] **Step 3: Write session.py**

Create `src/consult_interface/session.py`:

```python
"""CONSULT protocol logic, independent of how bytes are moved.

Sequence:
  1. init      -- write FF FF EF, expect the byte-inverted reply
  2. select    -- write 5A <reg> per parameter, terminated by F0
  3. header    -- the ECU echoes the selection with 5A markers inverted to A5
  4. stream    -- repeating FF <data_len> <data bytes...>
  5. stop      -- write 30
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping

from .definition import ConsultDefinition, ParamID
from .frames import FrameLayout, FrameParser, invert_bytes
from .params import ParamSpec
from .transport import Transport

log = logging.getLogger(__name__)


class InitializeFailedError(ValueError):
    """The ECU did not answer the init handshake with the inverted command."""


class ConsultSession:
    """Speaks CONSULT over any Transport."""

    def __init__(self, transport: Transport, definition: ConsultDefinition | None = None) -> None:
        self._transport = transport
        self._definition = definition or ConsultDefinition()
        self._initialized = False

    @property
    def definition(self) -> ConsultDefinition:
        return self._definition

    def initialize(self) -> bool:
        """Perform the FF FF EF handshake."""
        if not self._transport.is_connected():
            self._transport.open()

        command = bytes(self._definition.init)
        self._transport.write(command)

        expected = bytes(invert_bytes(command))
        response = self._transport.read(len(expected))
        if response != expected:
            raise InitializeFailedError(
                f"unexpected init response: {response.hex(' ').upper()} "
                f"(expected {expected.hex(' ').upper()})"
            )
        self._initialized = True
        return True

    def select(self, param_ids: Iterable[ParamID]) -> FrameParser:
        """Request parameters and return a parser built from the ECU's echo."""
        # Narrow explicitly -- mypy --strict cannot follow Optional through a
        # list comprehension guarded by any().
        specs: list[ParamSpec] = []
        for pid in param_ids:
            spec = self._definition.get_parameter(pid)
            if spec is None:
                raise ValueError(f"unknown ParamID: {pid!r}")
            specs.append(spec)

        command = bytearray()
        for spec in specs:
            command.append(self._definition.cmd_register_param)
            command.append(spec.register)
        command.append(self._definition.start_stream)
        self._transport.write(bytes(command))

        # The echo is one A5 <reg> pair per selected register.
        header = self._transport.read((len(command) - 1))
        layout = FrameLayout.from_header(header)
        return FrameParser(layout, specs)

    def read_frame(self, parser: FrameParser) -> Mapping[ParamID, float | int]:
        """Read and decode exactly one frame."""
        frame = self._transport.read(len(parser.layout) + 2)
        return parser.decode(frame)

    def stop(self) -> None:
        """Tell the ECU to stop streaming."""
        self._transport.write(bytes([self._definition.stop_stream]))
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_transport.py -v`
Expected: PASS

- [ ] **Step 5: Update the public API**

Replace `src/consult_interface/__init__.py`:

```python
"""Host-side implementation of the Nissan CONSULT diagnostic protocol."""

from .definition import ConsultDefinition, ParamID, ParamTableError
from .frames import FrameLayout, FrameParser, RegisterNotInHeaderError
from .params import BitParam, DualParam, ParamSpec, SingleParam
from .session import ConsultSession, InitializeFailedError
from .transport import CaptureTransport, SerialTransport, Transport

__version__ = "0.2.0"

__all__ = [
    "BitParam",
    "CaptureTransport",
    "ConsultDefinition",
    "ConsultSession",
    "DualParam",
    "FrameLayout",
    "FrameParser",
    "InitializeFailedError",
    "ParamID",
    "ParamSpec",
    "ParamTableError",
    "RegisterNotInHeaderError",
    "SerialTransport",
    "SingleParam",
    "Transport",
]
```

- [ ] **Step 6: Delete the superseded modules**

```bash
git rm src/consult_interface/ci_serial.py src/consult_interface/utils.py
```

**Divergence from the spec, deliberate:** the spec's dissolution table routes
`param_ids_to_param` and `param_id_of_single_param` into `definition.py`. They are instead
subsumed — `ConsultSession.select` resolves ParamIDs to specs inline, and
`param_id_of_single_param` had no caller outside the deleted `tests/test_utils.py`. Adding
them as standalone lookups would be dead code on arrival.

- [ ] **Step 7: Confirm the contract still holds**

Run: `MPLBACKEND=Agg uv run pytest tests/test_golden.py tests/test_definition.py tests/test_frames.py tests/test_transport.py -v`
Expected: all PASS

`tests/test_frame.py` and `tests/test_utils.py` now fail on import — Task 9 removes them.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "Add ConsultSession and delete ci_serial.py/utils.py

Protocol logic separates from transport. Deletes the broken
read_ecu_part_number, the commented-out mock, and create(mock=True).
Public API re-exported from __init__ at 0.2.0."
```

---

### Task 9: Retire the old test files and the plotting tail

**Files:**
- Delete: `tests/test_frame.py`, `tests/test_utils.py`
- Modify: `tests/conftest.py`
- Modify: `tests/data_registry.py`

**Interfaces:**
- Consumes: everything from Tasks 4-8
- Produces: a suite with no references to the removed API

- [ ] **Step 1: Delete the superseded tests**

`test_frame.py` is replaced by `test_golden.py` (end-to-end) plus `test_frames.py` (units). `test_utils.py` tested `scan_match`, `invert_bytes`, and the command/param conversions — `invert_bytes` and the conversions are now covered in `test_frames.py` and `test_transport.py`, and `scan_match` is deleted with its only caller.

```bash
git rm tests/test_frame.py tests/test_utils.py
```

- [ ] **Step 2: Fix the deprecated logging calls in conftest.py**

In `tests/conftest.py`, replace both `logging.warn(...)` calls with `logging.warning(...)`:

```python
@pytest.fixture(scope="session")
def data_registry(project_root_path):
    logging.warning("INITIALIZATION")
    yield DataRegistry.get_registry(project_root_path)
    logging.warning("TEAR DOWN")
```

- [ ] **Step 3: Run the full suite**

Run: `uv run pytest -v`

Note: no `MPLBACKEND=Agg` needed any more — the plotting code left with `test_frame.py`. If the suite still blocks or imports matplotlib, something was missed.

Expected: all PASS, no matplotlib import anywhere in `tests/`.

- [ ] **Step 4: Verify matplotlib is genuinely unused by the suite**

Run: `grep -rn "matplotlib\|plt\." tests/ || echo "clean"`
Expected: `clean`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Retire old tests and the plotting tail

test_frame.py and test_utils.py are superseded by test_golden.py,
test_frames.py, and test_transport.py. Removing show_plot() means the
suite no longer needs MPLBACKEND=Agg."
```

---

### Task 10: Enforce mypy strict, refresh docs, final verification

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: everything
- Produces: a green CI running ruff + mypy --strict + pytest

- [ ] **Step 1: Run mypy and fix what it finds**

Run: `uv run mypy`

Expected: errors, most likely around `CaptureTransport._handle` (typed `object | None` but used as a file handle) and the `process_frame` callback in `ReadParamFramesThread`.

Fix them properly, not with `# type: ignore`:

```python
# transport.py
from typing import IO
from collections.abc import Callable

class CaptureTransport:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._handle: IO[bytes] | None = None
        self._written = bytearray()
```

```python
class ReadParamFramesThread(threading.Thread):
    def __init__(
        self,
        transport: Transport,
        frame_bytes: int,
        process_frame: Callable[[bytes], None],
    ) -> None:
```

Re-run `uv run mypy` until it reports `Success: no issues found`.

- [ ] **Step 2: Run ruff and fix what it finds**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: both clean. Fix any violations; `ruff check --fix` handles most.

- [ ] **Step 3: Add mypy to CI**

In `.github/workflows/ci.yml`, insert between the format check and the tests:

```yaml
    - name: Type check
      run: uv run mypy
```

And drop the now-unnecessary env block from the test step:

```yaml
    - name: Run tests
      run: uv run pytest
```

- [ ] **Step 4: Update CLAUDE.md**

The Architecture section describes the old design and is now wrong. Replace the "Modules", "Shared mutable state", and "Known rough edges" sections:

````markdown
### Modules

- **`definition.py`** — `ParamID` IntEnum and `ConsultDefinition`, which loads `params.toml`
  via `tomllib`, validates it (ParamID bijection, register range, duplicate register/bit),
  and exposes the lookups.
- **`params.toml`** — the parameter table. Authoritative. `docs/params.csv` is human
  reference material and is NOT loaded at runtime.
- **`params.py`** — frozen `ParamSpec` descriptors: `SingleParam`, `DualParam` (MSB+LSB as
  `msb << 8 | lsb`), `BitParam`. They hold no value state; `decode(layout, frame)` returns one.
- **`frames.py`** — byte helpers, `FrameLayout.from_header()` (parses the `A5 <reg>` echo),
  and `FrameParser.decode(frame) -> {ParamID: value}`.
- **`transport.py`** — `Transport` Protocol plus `SerialTransport` (pyserial) and
  `CaptureTransport` (replays a `.hex` capture). Add a transport by satisfying the Protocol.
- **`session.py`** — `ConsultSession`: init handshake, register selection, streaming, stop.
- **`cli/`** — Click group auto-discovering `cli/commands/cmd_*.py`. Still a scaffold.

### Decoding is stateless

There is no global mutable state and no `enabled` flag. Decoding is
`ConsultDefinition()` → `session.select(param_ids)` → `parser.decode(frame)`, which returns
a fresh `{ParamID: value}` mapping. Parsers are cheap; construct one per selection.

### Preserved quirks

Deliberate, enforced by `tests/test_golden.py` — do not "fix" them without a new capture to
re-baseline against:

- `DualParam` substitutes `0` for a missing MSB or LSB, raising only when both are absent.
- `BitParam` returns the raw bit, ignoring scale and offset.
- Frame sanity failures log and continue rather than raising.
- The register→ParamID map is last-wins, so register `0x13` resolves only to `CLSD_THL_POS`
  and `0x21` only to `RH_BANK_LEAN`. Five bit params are unreachable that way. Probably a
  latent bug; fixing it would decode extra parameters and break the golden contract.

### Disputed parameter values

`BATTERY_VOLTAGE`, `TPS`, and `VEHICLE_SPEED` carry a `disputed` note in `params.toml` where
the code disagrees with `docs/params.csv` about units. Values are kept at the code's original
figures pending confirmation on a real ECU. `BATTERY_VOLTAGE` decodes to ~14240 labelled "V",
which is almost certainly millivolts.
````

Also update the Commands block: the suite no longer needs `MPLBACKEND=Agg`, so delete that
paragraph, and add:

```bash
uv run ruff check . && uv run ruff format .   # lint and format
uv run mypy                                    # strict type check over src/
```

- [ ] **Step 5: Update README.md**

The README is one line (`consult-interface`). Replace it:

```markdown
# consult-interface

Host-side implementation of the Nissan CONSULT diagnostic protocol — 9600-baud
serial to an ECU over a USB adapter.

## Quick start

```bash
uv sync
uv run pytest
```

## Reading a capture without hardware

```python
from pathlib import Path
from consult_interface import CaptureTransport, ConsultSession, ParamID

session = ConsultSession(CaptureTransport(Path("docs/test_data.hex")))
parser = session.select([ParamID.ENGINE_SPEED_HR, ParamID.COOLANT_TEMP])
print(session.read_frame(parser))
```

Protocol reference material lives in `docs/` — **Issue 7 is the newest**.
```

- [ ] **Step 6: Full verification**

Run each and confirm:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -v
uv build
```

Expected: ruff clean, mypy `Success: no issues found`, all tests pass including
`test_golden.py`, and `uv build` produces a wheel and sdist. Then `rm -rf dist`.

- [ ] **Step 7: Confirm no stale references remain**

Run: `grep -rn "EcuParam\|ci_serial\|utils\.\|update_value\|get_enabled_parameters" src/ tests/ || echo "clean"`
Expected: `clean`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "Enforce mypy --strict in CI and refresh docs

CLAUDE.md and README.md rewritten for the new architecture, including
the preserved quirks and disputed parameter values."
```

---

## Definition of Done

- [ ] `uv run pytest` passes with no `MPLBACKEND` workaround
- [ ] `tests/test_golden.py` passes — decoded output is byte-identical to pre-refactor
- [ ] `uv run mypy` reports no issues under `--strict`
- [ ] `uv run ruff check .` and `uv run ruff format --check .` are clean
- [ ] `uv build` produces a valid wheel and sdist
- [ ] No references to `EcuParam`, `ci_serial`, `utils`, or `update_value` remain
- [ ] `concept/` and `mock_ecu/` are untouched
- [ ] CI is green on both 3.12 and 3.13
