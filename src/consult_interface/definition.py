import tomllib
from enum import IntEnum
from pathlib import Path

from .params import BitParam, DualParam, ParamSpec, SingleParam

TABLE_PATH = Path(__file__).with_name("params.toml")


class ParamID(IntEnum):
    ENGINE_SPEED_HR = 0
    ENGINE_SPEED_LR = 1
    MAF_VOLTAGE = 2
    MAF_VOLTAGE_RH = 3
    COOLANT_TEMP = 4
    O2_VOLTAGE_LH = 5
    O2_VOLTAGE_RH = 6
    VEHICLE_SPEED = 7
    BATTERY_VOLTAGE = 8
    TPS = 9
    FUEL_TEMP = 10
    IAT = 11
    EGT = 12
    INJECTOR_TIME_LH = 13
    IGNITION_TIMING = 14
    AAC_VALVE = 15
    AF_ALPHA_LH = 16
    AF_ALPHA_RH = 17
    AF_ALPHA_SELFLEARN_LH = 18
    AF_ALPHA_SELFLEARN_RH = 19
    INJECTOR_TIME_RH = 20
    PURGE_VALVE_STEP = 21
    TANK_FUEL_TEMP = 22
    FPCM_VOLTAGE = 23
    WG_SOLENOID_POS = 24
    BOOST_VOLTAGE = 25
    ENGINE_MOUNT = 26
    POSITION_COUNTER = 27
    FUEL_GAUGE_VOLTAGE = 28
    O2_FRONT_B1_VOLTAGE = 29
    O2_FRONT_B2_VOLTAGE = 30
    IGNITION_SWITCH = 31
    CAL_LD_VALUE = 32
    FUEL_SCHEDULE = 33
    O2_REAR_B1_VOLTAGE = 34
    O2_REAR_B2_VOLTAGE = 35
    THROTTLE_POSITION_ABS = 36
    MAF_SCALED = 37
    EVAP_PRESSURE_VOLTAGE = 38
    ABS_PRESSURE_VOLTAGE_A = 39
    ABS_PRESSURE_VOLTAGE_B = 40
    FPCM_PRESSURE_VOLTAGE_A = 41
    FPCM_PRESSURE_VOLTAGE_B = 42
    AC_ON = 43
    POWER_STEERING = 44
    PARK_NEUTRAL = 45
    CRANKING = 46
    CLSD_THL_POS = 47
    AC_RELAY = 48
    FUEL_PUMP_RELAY = 49
    VTC_SOLENOID = 50
    COOLANT_FAN_HI = 51
    COOLANT_FAN_LO = 52
    P_REG_CONTROL_VALVE = 53
    WG_SOLENOID_STATE = 54
    IACV_FICD_SOLENOID = 55
    EGR_SOLENOID = 56
    LH_BANK_LEAN = 57
    RH_BANK_LEAN = 58


class ParamTableError(ValueError):
    """Raised when params.toml is malformed or disagrees with ParamID."""


class ConsultDefinition:
    def __init__(self, table_path: Path | None = None) -> None:
        self.init = [0xFF, 0xFF, 0xEF]
        self.cmd_ecu_part_number = 0xD0
        self.cmd_register_param = 0x5A
        self.start_stream = 0xF0
        self.stop_stream = 0x30

        self._parameters: dict[ParamID, ParamSpec] = {}
        self._disputed: dict[ParamID, str] = {}
        self._load(table_path or TABLE_PATH)
        self._validate()

        self._register_to_param_id_dict: dict[int, ParamID] = {}
        for pid, p in self._parameters.items():
            # Last-wins, deliberately: preserves the original reverse-map behaviour
            # where several bit params share one register.
            self._register_to_param_id_dict[p.register] = pid

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
                param: ParamSpec = SingleParam(
                    param_id=pid,
                    name=name,
                    unit=unit,
                    scale=scale,
                    offset=offset,
                    register_addr=row["register"],
                )
            elif kind == "dual":
                param = DualParam(
                    param_id=pid,
                    name=name,
                    unit=unit,
                    scale=scale,
                    offset=offset,
                    register_msb=row["register_msb"],
                    register_lsb=row["register_lsb"],
                )
            elif kind == "bit":
                bit = row["bit"]
                if not 0 <= bit <= 7:
                    raise ParamTableError(f"{pid.name}: bit {bit} out of range 0-7")
                param = BitParam(param_id=pid, name=name, register_addr=row["register"], bit=bit)
            else:
                raise ParamTableError(f"{pid.name}: unknown kind {kind!r}")

            for reg in param.registers:
                if not 0x00 <= reg <= 0xFF:
                    raise ParamTableError(f"{pid.name}: register 0x{reg:X} out of range")

            self._parameters[pid] = param
            if note := row.get("disputed"):
                self._disputed[pid] = note

    def _validate(self) -> None:
        missing = set(ParamID) - set(self._parameters)
        if missing:
            raise ParamTableError(
                "params.toml is missing rows for: " + ", ".join(sorted(m.name for m in missing))
            )

        seen: set[tuple[tuple[int, ...], int | None]] = set()
        for p in self._parameters.values():
            key = (p.registers, p.bit if isinstance(p, BitParam) else None)
            if key in seen:
                raise ParamTableError(f"duplicate register/bit combination: {p.name}")
            seen.add(key)

    def disputed_note(self, pid: ParamID) -> str | None:
        """Return the params.csv conflict note for this param, if any."""
        return self._disputed.get(pid)

    def get_param_id_from_register(self, register: int) -> ParamID | None:
        if register not in self._register_to_param_id_dict:
            return None
        return self._register_to_param_id_dict[register]

    def get_parameter_from_register(self, register: int) -> ParamSpec | None:
        pid = self.get_param_id_from_register(register)
        if pid is None or pid not in self._parameters:
            return None
        return self._parameters[pid]

    def get_parameter_from_param_id(self, pid: ParamID) -> ParamSpec | None:
        if pid not in self._parameters:
            return None
        return self._parameters[pid]

    def get_parameter(self, pid: ParamID) -> ParamSpec | None:
        if isinstance(pid, ParamID):
            return self.get_parameter_from_param_id(pid)
        raise TypeError(f"Expected ParamID, got {type(pid)}")

    def get_parameter_list(self) -> list[ParamSpec]:
        return list(self._parameters.values())

    def get_parameter_dict(self) -> dict[ParamID, ParamSpec]:
        return self._parameters
