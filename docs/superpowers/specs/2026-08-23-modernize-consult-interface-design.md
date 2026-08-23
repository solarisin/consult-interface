# Modernize consult-interface: Python 3.12+ and structural restructure

**Date:** 2026-08-23
**Status:** Approved for planning
**Branch:** stacked on `migrate-to-uv` (which must merge first)

## Context

`consult-interface` is a host-side implementation of the Nissan CONSULT diagnostic
protocol. The package works, but it carries structural debt from its origins as
scratch code extracted from a GUI viewer project:

- A process-wide mutable `Definition` singleton whose `EcuParam` objects are mutated
  in place by `enable()` and `update_value()`. Decoding a frame means enabling params
  on the global registry and reading values back off the same objects — order-dependent
  and not thread-safe.
- A 60-line imperative parameter table built by repeated `self._parameters[X] = ...`
  assignments inside `ConsultDefinition.__init__`.
- `ci_serial.py` mixes byte transport with protocol logic, and contains dead code
  (`read_ecu_part_number`, a commented-out mock transport, a `create(mock=True)` branch
  that only raises).
- Two genuine bugs: `utils.param_ids_to_param(param_ids: iter(ParamID))` calls `iter()`
  on the enum class at definition time, and `ReadParamFramesThread.run` tests
  `if not self._port.open()` when `Serial.open()` returns `None`.
- Loose typing throughout (`-> (bool, bytearray)` instead of `tuple[bool, bytearray]`),
  `print()` on error paths, a bare `except:`, an unused import, `id` shadowing the builtin.

The project has just migrated from Poetry to uv. This is the follow-on: retarget to
Python 3.12+ and restructure the code.

## Goals

1. Target Python 3.12+.
2. Replace mutable shared parameter state with immutable descriptors and a decoder that
   returns values.
3. Move the parameter table out of Python into a checked-in TOML data file.
4. Separate transport from protocol logic; make the transport a `Protocol`.
5. Add a real mock transport that replays capture files.
6. Full static typing, enforced by `mypy --strict` and `ruff` in CI.
7. Rewrite and expand the test suite.

## Non-goals

- **Changing any decoded value.** See "Behavioural invariant" below. This is a pure
  refactor with respect to output.
- Resolving the three code-vs-CSV unit conflicts. They are recorded, not fixed.
- Implementing `read_ecu_part_number`. It is deleted, not rewritten.
- Building CLI features. The CLI stays a scaffold.
- Touching `concept/` (scratch, kept for reference) or `mock_ecu/` (standalone script).

## Behavioural invariant

The decisive constraint: **decoded output must be identical before and after.**

Enforced by a golden-output test built *before* any restructuring:

1. On the current code, decode every frame in `docs/test_data.hex` using the `test_1`
   command from the data registry.
2. Serialize as `{param_name: value}` per frame — deliberately NOT `EcuParam.to_dict()`,
   so the golden file does not couple to a serialization shape that is about to change.
3. Store `tests/golden/test_1_decoded.json` containing a deterministic sample (every
   500th frame, plus the first and last 10) and a SHA-256 over the full decoded stream.
4. Commit that file as its own commit, before the refactor begins.
5. `tests/test_golden.py` reproduces it through the new API and asserts equality.

**Existing quirks are preserved deliberately**, because they are part of current output:

- `DualParam` substitutes `0` for a missing MSB or LSB and only raises
  `RegisterNotInHeaderError` when both are absent.
- `BitParam.get_value()` returns the raw bit, bypassing scale/offset.
- Frame sanity-check failures log an error and continue rather than raising.

If the golden test forces a choice between "clean" and "identical", identical wins.
Anything that cannot be preserved must be raised before proceeding, not silently changed.

## Architecture

### Layout

```
src/consult_interface/
  __init__.py      public API re-exports
  definition.py    ParamID, ConsultDefinition (TOML-backed registry)
  params.py        ParamSpec frozen dataclasses
  params.toml      the parameter data table
  frames.py        FrameLayout, FrameParser
  transport.py     Transport Protocol, SerialTransport, CaptureTransport
  session.py       ConsultSession (init handshake, register select, stream, stop)
  cli/             unchanged in behaviour; auto-discovery of cmd_*.py retained
```

`utils.py` is dissolved, function by function:

| Current `utils.py` | Destination |
|---|---|
| `invert_byte`, `invert_bytes`, `bytes_to_str` | `frames.py` |
| `params_to_command`, `command_to_params` | `session.py` |
| `param_ids_to_param`, `param_id_of_single_param` | `definition.py` (lookups on the registry) |
| `scan_match` | deleted — its only live caller was the commented-out mock; `tests/test_utils.py::test_scan_match` goes with it |
| `Definition` singleton | replaced by the immutable module default in `definition.py` |

### Data model

`ParamSpec` is a frozen dataclass hierarchy — pure description, no value state, no
`enabled` flag:

- `SingleParam(param_id, name, register, unit, scale, offset)`
- `DualParam(param_id, name, register_msb, register_lsb, unit, scale, offset)`
- `BitParam(param_id, name, register, bit)`

Each exposes `registers -> tuple[int, ...]` and `register -> int` (LSB for dual, matching
today's semantics). The `Ecu` prefix is dropped as redundant.

`FrameLayout.from_header(header)` parses the `A5 <reg> A5 <reg> ...` echo into an ordered
tuple of registers, replacing the `header[1::2]` slice currently repeated inline.

`FrameParser(layout, specs)` exposes `decode(frame) -> dict[ParamID, float | int]`.
Returning values rather than mutating shared objects is what removes the ordering and
thread-safety hazards.

`decode` returns one entry per spec it was constructed with. A spec whose register is
absent from the layout raises `RegisterNotInHeaderError`, matching today's
`EcuParam.extract_value` — except for `DualParam`, which preserves the substitution quirk
described above and raises only when both its registers are absent.

`ConsultDefinition` loads `params.toml` into frozen specs, validates, and exposes lookups.
A module-level default instance remains for convenience — safe now that it is immutable.

### Parameter table: TOML schema

`ParamID` stays a Python `IntEnum` (static typing needs it declared). TOML rows reference
members by name, and validation asserts a bijection between enum members and TOML rows.

```toml
schema_version = 1

[[param]]
id = "ENGINE_SPEED_HR"
kind = "dual"
name = "Engine Speed HR"
register_msb = 0x00
register_lsb = 0x01
unit = "RPM"
scale = 12.5

[[param]]
id = "COOLANT_TEMP"
kind = "single"
name = "Coolant Temp"
register = 0x08
unit = "C"
offset = -50

[[param]]
id = "AC_ON"
kind = "bit"
name = "A/C On"
register = 0x13
bit = 4

[[param]]
id = "BATTERY_VOLTAGE"
kind = "single"
name = "Battery Voltage"
register = 0x0C
unit = "V"
scale = 80
disputed = "params.csv says Value * 80 (mV); the V label may be wrong"
```

Defaults: `scale = 1.0`, `offset = 0.0`, `unit = ""`.

Validation, at construction, raising on failure:

- every `id` resolves to a `ParamID` member, and every member appears exactly once
- `kind` is one of `single` / `dual` / `bit`
- registers are `0x00`–`0xFF`; `bit` is `0`–`7`
- the `(registers, bit)` combination is unique (preserving today's sanity check)
- fields present match the declared `kind`

The table is generated from the current Python table, so values port verbatim.

### Disputed rows

Three parameters conflict with `docs/params.csv`. They carry a `disputed` field and are
asserted by a test so they stay visible:

| Register | Param | Code (kept) | params.csv says |
|---|---|---|---|
| `0x0B` | Vehicle Speed | `km/h`, scale 2 | `Value * 2 (kph)` — cosmetic only |
| `0x0C` | Battery Voltage | `V`, scale 80 | `Value * 80 (mV)` — label likely wrong |
| `0x0D` | TPS | `%`, scale 20 | `Value * 20 (mV)` — genuine conflict |

`docs/params.csv` remains reference material. It is not loaded at runtime: 31 of its 62
rows carry no usable formula (16 `NULL`, 9 `Not documented`, 6 `See LSB`), the formulas it
does have are free-text English, and it has its own slug typo (`maf_volts_rh_msb` used for
both `0x06` and `0x07`).

### Transport and session

`ConsultSerial` (ABC) becomes `Transport` (`typing.Protocol`) with `open`, `close`, `read`,
`write`, `is_connected`.

- `SerialTransport` — pyserial. No longer spawns a thread from its constructor.
- `CaptureTransport` — replays a `.hex` capture, promoting `test_frame.py`'s local
  `MockConsultSerial` into a supported part of the package.

`ConsultSession` holds protocol logic: `FF FF EF` init handshake and inverted-response
check, `5A <reg>` selection terminated by `F0`, header echo capture, frame streaming, `30`
stop. `ReadParamFramesThread` moves to `transport.py` (it is a byte-pump, not protocol
logic) and keeps its role with the `Serial.open()` truthiness bug fixed.

Deleted: `read_ecu_part_number`, the commented-out `ConsultSerialMock`, `create(mock=True)`.

## Public API change

Version bumps to **0.2.0**. No deprecation shims.

| Before | After |
|---|---|
| `Definition` (mutable global) | `ConsultDefinition()` instance; immutable module default |
| `param.enable()` | selection passed explicitly to the session/parser |
| `param.update_value(header, frame)` | `FrameParser.decode(frame) -> dict[ParamID, ...]` |
| `param.get_value()` | value read from the returned mapping |
| `EcuParamSingle` / `Dual` / `Bit` | `SingleParam` / `DualParam` / `BitParam` |
| `ci_serial.ConsultSerial` (ABC) | `transport.Transport` (Protocol) |
| `ci_serial.create(port, mock=False)` | `SerialTransport(port)` / `CaptureTransport(path)` |

## Testing

Replacing the single 120-line `test_decode_response`:

- `test_definition.py` — TOML loads; enum/TOML bijection; duplicate registers rejected;
  malformed rows rejected; disputed rows carry their note.
- `test_frames.py` — layout parsing from a header echo; single/dual/bit decode; error
  paths (register absent from header, short frame, bad start byte); the dual
  missing-MSB/LSB substitution quirk.
- `test_transport.py` — `CaptureTransport` replay, init handshake, stop.
- `test_golden.py` — the behavioural invariant.

The plotting tail (`show_plot` / `plt.show()`) is removed. It is a debugging aid, not an
assertion, and it is the reason the suite currently needs `MPLBACKEND=Agg`. matplotlib
moves to the dev dependency group. If plotting is wanted later, `cli plot <capture>` is
its natural home — not built here.

## Tooling

- `requires-python = ">=3.12"`; `.python-version` pins 3.12; uv manages the interpreter
  (system Python on the dev Pi is 3.11.2, so uv downloads `cpython-3.12.x`).
- Ruff for lint and format. Mypy `--strict` over `src/` only.
- `concept/` and `mock_ecu/` excluded from both.
- CI: matrix on 3.12 and 3.13, running ruff check → ruff format --check → mypy → pytest.
- `timer` dependency dropped (unused anywhere in the repo).

## Risks

- **Silent value drift** — the golden test is the entire mitigation, which is why it lands
  before the refactor rather than after.
- **Capture coverage** — only one capture (`test_1`, 14 params) exists, so the golden test
  exercises those registers and no others. Params outside that command are covered only by
  unit tests over synthetic frames.
- **Interpreter download** — first `uv sync` on 3.12 pulls an interpreter on the Pi.
- **Stacked branch** — this work sits on `migrate-to-uv`; that branch merges first.

## Open questions

None blocking. Deferred by explicit decision: the physics of the three disputed rows,
which needs a real ECU rather than a code change.
