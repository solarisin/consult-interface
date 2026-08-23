# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

uv-managed Python 3.12+ project (`uv.lock` is committed; uv manages the interpreter, so
the system Python version does not matter).

```bash
uv sync                              # create/update .venv from the lock file
uv run pytest                        # full suite (43 tests, ~6s)
uv run pytest tests/test_golden.py   # the behavioural contract alone
uv run ruff check . && uv run ruff format .   # lint and format
uv run mypy                          # strict type check over src/
uv run cli params                    # the Click CLI entry point
uv add <pkg> / uv add --dev <pkg>    # dev deps live in [dependency-groups].dev
```

`pyproject.toml` sets `log_cli = true` at DEBUG, so pytest output is verbose by design.

Docker (GUI viewer image, X11 passthrough):

```bash
docker/build && docker/start
```

Note the Dockerfile is stale independently of this: it copies `./src/mainview.py` and
PySide6 system deps left over from the consult-viewer project, neither of which exists here.

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
`ConsultSession(transport)` → `session.select(param_ids)` → `parser.decode(frame)`, which
returns a fresh `{ParamID: value}` mapping. Parsers are cheap; construct one per selection.

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

## The golden contract

`tests/test_golden.py` decodes all 39,147 frames of `docs/test_data.hex` and compares against
`tests/golden/test_1_decoded.json` — a sampled table plus a SHA-256 over the full stream,
frozen before the 3.12 refactor.

**Never regenerate that file to make a failing test pass.** A diff means decoded output
changed, which is a bug unless you intended it. If you intend it, re-baseline deliberately
and say so in the commit.

## Testing against captures

No hardware in the test loop. `CaptureTransport` replays a `.hex` capture through the same
`Transport` protocol the real serial link uses. Capture files start *after* the command was
sent and contain no init sequence, so `select()` reads the ECU's header echo straight from
the file and `initialize()` is skipped.

Replaying a capture requires selecting the same parameters, in the same order, that produced
it — the header echo defines the frame layout, so a different selection decodes garbage.

`tests/data_registry.py` maps a name → (command bytes sent, capture file); `tests/conftest.py`
exposes it as the session-scoped `data_registry` fixture.

`mock_ecu/` is a separate script. Despite its name it does not serve a serial port — it only
pretty-prints `behaviors.json`. It is not imported by the package or the tests.

## Reference material and scratch code

- `docs/` holds the authoritative protocol PDFs (**Issue 7 is the newest**), `params.csv`
  (register table), and pinout/schematic material. When adding or correcting a parameter's
  register, scale, or offset, check these rather than inferring from existing entries.
- `docs/superpowers/` holds the design spec and implementation plan for the 3.12 modernization.
- `concept/` is exploratory scratch code kept for reference — standalone scripts, not part of
  the package. Excluded from ruff and mypy. Don't refactor or lint it as if it were library code.
