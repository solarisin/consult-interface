# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

uv-managed Python 3.10+ project (`uv.lock` is committed; there is no Poetry setup any more).

```bash
uv sync                              # create/update .venv from the lock file
uv run pytest                        # full suite (6 tests, ~8s)
uv run pytest tests/test_frame.py::test_decode_response   # single test
uv run pytest -q --html=report.html  # pytest-html report (title set in conftest.py)
uv run cli params                    # the Click CLI entry point (see pyproject [project.scripts])
uv add <pkg> / uv add --dev <pkg>    # dev deps live in [dependency-groups].dev
```

`pyproject.toml` sets `log_cli = true` at DEBUG, so pytest output is very verbose by design — tests use logging as their primary output channel, not just assertions.

**Set `MPLBACKEND=Agg` when running the suite on a machine with a display.** The tail of `test_decode_response` calls `show_plot()` (`plt.show()`) once per enabled parameter, which blocks on an interactive backend.

Docker (GUI viewer image, X11 passthrough):

```bash
docker/build && docker/start
```

## Architecture

This is a host-side implementation of the **Nissan CONSULT** diagnostic protocol — 9600-baud serial to an ECU over a USB adapter.

### The protocol, end to end

Understanding this sequence explains most of the code:

1. **Init handshake** — write `FF FF EF`; the ECU replies with the byte-inverted command (`00 00 10`). See `ConsultSerial.initialize_ecu`.
2. **Register selection** — write `5A <reg>` per parameter you want, terminated by `F0` (start stream). Built by `utils.params_to_command`.
3. **Header echo** — the ECU echoes the selection back with the `5A` marker bytes inverted to `A5`, register bytes unchanged: `A5 <reg> A5 <reg> ...`. This echo *is* the frame layout descriptor.
4. **Frame stream** — repeating `FF <data_len> <data bytes...>`, one data byte per selected register, in header order.
5. **Stop** — write `30`.

Frame decoding therefore always needs **both** the header and the frame: `EcuParam.extract_value` slices `header[1::2]` to recover the register order, finds the parameter's index there, and reads that index out of `frame[2:]`.

### Modules

- **`definition.py`** — `ConsultDefinition` holds the command bytes and the full ECU parameter table (register addresses, units, scale, offset), keyed by the `ParamID` IntEnum. Its constructor runs a sanity check rejecting duplicate (registers, bit) combinations, and builds the register→`ParamID` reverse map.
- **`params.py`** — `EcuParam` hierarchy. `EcuParamSingle` (one register), `EcuParamDual` (MSB+LSB combined as `msb << 8 | lsb`), `EcuParamBit` (one bit of a status register). Scaling is `unscaled * scale + offset`; `EcuParamBit` overrides `get_value` to return the raw bit.
- **`utils.py`** — command↔parameter conversion, byte inversion helpers, and the module-level `Definition` singleton.
- **`ci_serial.py`** — `ConsultSerial` ABC (protocol logic, transport-agnostic) plus `ConsultSerialImpl` (real `pyserial`) and `ReadParamFramesThread`. Subclass the ABC and implement `_open/_close/_read/_write/is_connected` to add a transport; `tests/test_frame.py::MockConsultSerial` is the working example.
- **`cli/`** — Click multi-command group that auto-discovers `cli/commands/cmd_*.py` by filename. Adding a command means adding a `cmd_<name>.py` exporting `cli`; nothing else needs registering. Currently a scaffold.

### Shared mutable state

`Definition` is a **process-wide singleton**, and the `EcuParam` objects it owns are stateful: `enable()` and `update_value()` mutate them in place. Decoding a frame means enabling the relevant params on the global `Definition` and then reading values back off those same objects. Anything touching parameter state is order-dependent and not thread-safe.

### Dual-register caveat

`get_register()` returns the **LSB** for dual parameters, and the register→`ParamID` map is built from `get_register()` only — so an MSB register looked up via `get_parameter_from_register` returns `None`. `EcuParamDual.update_value` tolerates a missing MSB or LSB in the header (substituting 0) and only raises `RegisterNotInHeaderError` when both are absent.

## Testing against captures

There is no hardware in the test loop. Tests replay raw byte captures:

- `tests/data_registry.py` maps a name → (command bytes sent, capture file). Add new captures there.
- `tests/conftest.py` exposes it as the session-scoped `data_registry` fixture, rooted at pytest's `rootpath`.
- Capture files (e.g. `docs/test_data.hex`) are raw ECU output starting *after* the command was sent, with no init sequence.

`mock_ecu/` is a separate script that replays scripted responses from `behaviors.json` over a serial port. It opens `behaviors.json` by relative path, so run it from inside `mock_ecu/`. It is not imported by the package or the tests.

## Reference material and scratch code

- `docs/` holds the authoritative protocol PDFs (**Issue 7 is the newest**), `params.csv` (register table), and pinout/schematic material. When adding or correcting a parameter's register, scale, or offset, check these rather than inferring from existing entries.
- `concept/` is exploratory scratch code kept for reference — standalone scripts, not part of the package. Don't refactor or lint it as if it were library code.

## Known rough edges

Pre-existing, not regressions — leave them alone unless the task is to fix them:

- `ci_serial.create(port, mock=True)` raises `NotImplementedError`; the mock transport at the bottom of `ci_serial.py` is commented out.
- `ConsultSerial.read_ecu_part_number` is dead code — it takes `port` instead of `self` and references undefined `process_frame` / `InvalidAckError`.
- `test_frame.py` carries a `# TODO - values are incorrect` on the decoded output; frame-value scaling is not yet trusted end to end.
