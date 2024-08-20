from .params import EcuParam, EcuParamSingle, EcuParamDual, EcuParamBit
from enum import IntEnum


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


class ConsultDefinition:
    def __init__(self):
        self.init = b'\xFF\xFF\xEF'
        self.init_response = 0x10
        # flag to be prefixed before any register value
        self.msg_register_param = 0x5A
        # terminates registration of values, and also signals the ecu our message is complete, and to start processing
        self.terminate_msg = 0xF0
        # ex: \x5A\x0B\x5A\x01 -> sets requested registers to b'0x0B' and b'0x01' (vehicle speed and engine speed),
        # then instructs the ECU to start streaming data
        self.stop_stream = 0x30
        self.stop_ack = 0xCF

        self._parameters = dict()
        self._parameters[ParamID.ENGINE_SPEED_HR] = EcuParamDual("Engine Speed HR", 0x00, 0x01, "RPM", 12.5)
        self._parameters[ParamID.ENGINE_SPEED_LR] = EcuParamDual("Engine Speed LR", 0x02, 0x03, "RPM", 8)
        self._parameters[ParamID.MAF_VOLTAGE] = EcuParamDual("MAF Voltage", 0x04, 0x05, "mV", 5)
        self._parameters[ParamID.MAF_VOLTAGE_RH] = EcuParamDual("MAF Voltage RH", 0x06, 0x07, "mV", 5)
        self._parameters[ParamID.COOLANT_TEMP] = EcuParamSingle("Coolant Temp", 0x08, "C", offset=-50)
        self._parameters[ParamID.O2_VOLTAGE_LH] = EcuParamSingle("O2 Voltage LH", 0x09, "mV", 10)
        self._parameters[ParamID.O2_VOLTAGE_RH] = EcuParamSingle("O2 Voltage RH", 0x0A, "mV", 10)
        self._parameters[ParamID.VEHICLE_SPEED] = EcuParamSingle("Vehicle Speed", 0x0B, "km/h", 2)
        self._parameters[ParamID.BATTERY_VOLTAGE] = EcuParamSingle("Battery Voltage", 0x0C, "V", 80)
        self._parameters[ParamID.TPS] = EcuParamSingle("TPS", 0x0D, "%", 20)
        self._parameters[ParamID.FUEL_TEMP] = EcuParamSingle("Fuel Temp", 0x0F, "C", offset=-50)
        self._parameters[ParamID.IAT] = EcuParamSingle("IAT", 0x11, "C", offset=-50)
        self._parameters[ParamID.EGT] = EcuParamSingle("EGT", 0x12, "mV", 20)
        self._parameters[ParamID.INJECTOR_TIME_LH] = EcuParamDual("Injector Time LH", 0x14, 0x15, "ms", 1/100)
        self._parameters[ParamID.IGNITION_TIMING] = EcuParamSingle("Ignition Timing", 0x16, "deg BTDC", -1, 110)
        self._parameters[ParamID.AAC_VALVE] = EcuParamSingle("AAC Valve", 0x17, "%", 1/2)
        self._parameters[ParamID.AF_ALPHA_LH] = EcuParamSingle("AF Alpha LH", 0x1A, "%")
        self._parameters[ParamID.AF_ALPHA_RH] = EcuParamSingle("AF Alpha RH", 0x1B, "%")
        self._parameters[ParamID.AF_ALPHA_SELFLEARN_LH] = EcuParamSingle("AF Alpha Selflearn LH", 0x1C, "%")
        self._parameters[ParamID.AF_ALPHA_SELFLEARN_RH] = EcuParamSingle("AF Alpha Selflearn RH", 0x1D, "%")
        self._parameters[ParamID.INJECTOR_TIME_RH] = EcuParamDual("Injector Time RH", 0x22, 0x23, "ms", 1/100)
        self._parameters[ParamID.PURGE_VALVE_STEP] = EcuParamSingle("Purge Valve Step", 0x25, "steps")
        self._parameters[ParamID.TANK_FUEL_TEMP] = EcuParamSingle("Tank Fuel Temp", 0x26)
        self._parameters[ParamID.FPCM_VOLTAGE] = EcuParamSingle("FPCM Voltage", 0x27, "V")
        self._parameters[ParamID.WG_SOLENOID_POS] = EcuParamSingle("WG Solenoid Pos", 0x28)
        self._parameters[ParamID.BOOST_VOLTAGE] = EcuParamSingle("Boost Voltage", 0x29, "V")
        self._parameters[ParamID.ENGINE_MOUNT] = EcuParamSingle("Engine Mount", 0x2A)
        self._parameters[ParamID.POSITION_COUNTER] = EcuParamSingle("Position Counter", 0x2E)
        self._parameters[ParamID.FUEL_GAUGE_VOLTAGE] = EcuParamSingle("Fuel Gauge Voltage", 0x2F, "V")
        self._parameters[ParamID.O2_FRONT_B1_VOLTAGE] = EcuParamSingle("O2 Front B1 Voltage", 0x30, "V")
        self._parameters[ParamID.O2_FRONT_B2_VOLTAGE] = EcuParamSingle("O2 Front B2 Voltage", 0x31, "V")
        self._parameters[ParamID.IGNITION_SWITCH] = EcuParamSingle("Ignition Switch", 0x32)
        self._parameters[ParamID.CAL_LD_VALUE] = EcuParamSingle("CAL LD Value", 0x33)
        self._parameters[ParamID.FUEL_SCHEDULE] = EcuParamSingle("Fuel Schedule", 0x34)
        self._parameters[ParamID.O2_REAR_B1_VOLTAGE] = EcuParamSingle("O2 Rear B1 Voltage", 0x35, "V")
        self._parameters[ParamID.O2_REAR_B2_VOLTAGE] = EcuParamSingle("O2 Rear B2 Voltage", 0x36, "V")
        self._parameters[ParamID.THROTTLE_POSITION_ABS] = EcuParamSingle("Throttle Position ABS", 0x37, "%")
        self._parameters[ParamID.MAF_SCALED] = EcuParamSingle("MAF Scaled", 0x38, "g/s")
        self._parameters[ParamID.EVAP_PRESSURE_VOLTAGE] = EcuParamSingle("Evap Pressure Voltage", 0x39, "V")
        self._parameters[ParamID.ABS_PRESSURE_VOLTAGE_A] = EcuParamSingle("ABS Pressure Voltage A", 0x3A, "V")
        self._parameters[ParamID.ABS_PRESSURE_VOLTAGE_B] = EcuParamSingle("ABS Pressure Voltage B", 0x4A, "V")
        self._parameters[ParamID.FPCM_PRESSURE_VOLTAGE_A] = EcuParamSingle("FPCM Pressure Voltage A", 0x52, "V")
        self._parameters[ParamID.FPCM_PRESSURE_VOLTAGE_B] = EcuParamSingle("FPCM Pressure Voltage B", 0x53, "V")
        self._parameters[ParamID.AC_ON] = EcuParamBit("A/C On", 0x13, 4)
        self._parameters[ParamID.POWER_STEERING] = EcuParamBit("Power Steering", 0x13, 3)
        self._parameters[ParamID.PARK_NEUTRAL] = EcuParamBit("Park/Neutral", 0x13, 2)
        self._parameters[ParamID.CRANKING] = EcuParamBit("Cranking", 0x13, 1)
        self._parameters[ParamID.CLSD_THL_POS] = EcuParamBit("CLSD/THL POS", 0x13, 0)
        self._parameters[ParamID.AC_RELAY] = EcuParamBit("A/C Relay", 0x1e, 7)
        self._parameters[ParamID.FUEL_PUMP_RELAY] = EcuParamBit("Fuel Pump Relay", 0x1e, 6)
        self._parameters[ParamID.VTC_SOLENOID] = EcuParamBit("VTC Solenoid", 0x1e, 5)
        self._parameters[ParamID.COOLANT_FAN_HI] = EcuParamBit("Coolant Fan Hi", 0x1e, 1)
        self._parameters[ParamID.COOLANT_FAN_LO] = EcuParamBit("Coolant Fan Lo", 0x1e, 0)
        self._parameters[ParamID.P_REG_CONTROL_VALVE] = EcuParamBit("P/Reg control valve", 0x1f, 6)
        self._parameters[ParamID.WG_SOLENOID_STATE] = EcuParamBit("WG Solenoid State", 0x1f, 5)
        self._parameters[ParamID.IACV_FICD_SOLENOID] = EcuParamBit("IACV FICD Solenoid", 0x1f, 3)
        self._parameters[ParamID.EGR_SOLENOID] = EcuParamBit("EGR Solenoid", 0x1f, 0)
        self._parameters[ParamID.LH_BANK_LEAN] = EcuParamBit("LH Bank Lean", 0x21, 7)
        self._parameters[ParamID.RH_BANK_LEAN] = EcuParamBit("RH Bank Lean", 0x21, 6)

        # perform a param sanity check -combination of registers + bit positions must be unique
        seen = set()
        for id, p in self._parameters.items():
            registers = p.get_registers()
            key = (registers, p.bit if isinstance(p, EcuParamBit) else None)
            if key in seen:
                raise ValueError(f"ECU parameter Sanity Check failed: Duplicate parameter: {p.name}")
            seen.add(key)

        # create a dict containing register -> param_id mappings. THis only contains the mapping for LSB
        # registers of dual parameters
        self._register_to_param_id_dict = dict()
        for pid, p in self._parameters.items():
            self._register_to_param_id_dict[p.get_register()] = pid

    def get_param_id_from_register(self, register: int) -> ParamID | None:
        if register not in self._register_to_param_id_dict:
            return None
        return self._register_to_param_id_dict[register]

    def get_parameter_from_register(self, register: int) -> EcuParam | None:
        pid = self.get_param_id_from_register(register)
        if pid is None or pid not in self._parameters:
            return None
        return self._parameters[pid]

    def get_parameter_from_param_id(self, pid: ParamID) -> EcuParam | None:
        if pid not in self._parameters:
            return None
        return self._parameters[pid]

    def get_parameter(self, pid: ParamID) -> EcuParam | None:
        if isinstance(pid, ParamID):
            return self.get_parameter_from_param_id(pid)
        raise TypeError(f"Expected ParamID, got {type(pid)}")

    def get_parameters(self) -> list[EcuParam]:
        return self._parameters.values()

    def get_enabled_parameters(self) -> list[EcuParam]:
        return [p for pid, p in self._parameters.items() if p.enabled]

    def count_enabled_parameters(self) -> int:
        return sum(1 for pid, p in self._parameters.items() if p.enabled)
