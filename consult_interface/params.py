import logging
from abc import ABC, abstractmethod

class EcuParam(ABC):
    def __init__(self, name, unit_label="", scale=1.0, offset=0.0):
        self.name = name
        self.unit_label = unit_label
        self.scale = scale
        self.offset = offset
        self.enabled = False

    @abstractmethod
    def get_registers(self) -> bytes:
        """
        Get the register bytes for this parameter, will be two bytes for dual parameters (MSB, LSB) and
        one byte for single parameters
        :return: the register bytes for this parameter
        """
        pass

    @abstractmethod
    def get_register(self) -> int:
        """
        Get the register for this parameter, guaranteed to be a single byte. LSB is used for dual parameters
        :return: the register byte for this parameter
        """
        pass

    @abstractmethod
    def update_value(self, header: bytes, frame: bytes):
        """
        Update the value of this parameter from the given frame
        :param header: the header of the frame
        :param frame: the frame data
        """
        pass

    @abstractmethod
    def get_unscaled_value(self):
        pass

    def get_value(self):
        unscaled = self.get_unscaled_value()
        if unscaled is None:
            return None
        return (unscaled * self.scale) + self.offset

    def enable(self, state=True):
        self.enabled = state

    @staticmethod
    def sanity_check(header: bytes, frame: bytes):
        # do some sanity checks on the header/frame...
        # frame should start with 0xFF
        if not frame[0] == 0xFF:
            logging.error(f"Invalid frame start byte: {frame.hex(' ')}")
        # the next byte should be the frame length
        frame_data_bytes = frame[1]
        # verify the occurrences of \xA5 equals the frame bytes
        param_count = header.count(b'\xA5')
        if param_count != frame_data_bytes:
            logging.error(f"Invalid frame byte count: {frame.hex(' ')}")

    @staticmethod
    def extract_value(header: bytes, frame: bytes, register: int):
        # bytes 1 and 2 are 0xFF and the frame length, respectively
        frame_data = frame[2:]
        # header is in the form b'\xA5\x[register_1]\xA5\x[register_2]...' which corresponds to the order of
        # the bytes in the frame.
        # find the position of this parameter in the frame from the header
        param_index = header.index(bytes([register]))
        # get the unscaled value from the frame data
        return frame_data[param_index]


class EcuParamSingle(EcuParam):
    def __init__(self, name, register: int, unit_label="", scale=1, offset=0):
        super().__init__(name, unit_label, scale, offset)
        self.register = register
        self._unscaled_value = None

    def get_registers(self) -> bytes:
        return bytes(self.get_register())

    def get_register(self) -> int:
        return self.register

    def get_unscaled_value(self):
        return self._unscaled_value

    def update_value(self, header: bytes, frame: bytes):
        EcuParam.sanity_check(header, frame)
        self._unscaled_value = EcuParam.extract_value(header, frame, self.register)


class EcuParamDual(EcuParam):
    def __init__(self, name, register_msb: int, register_lsb: int, unit_label="", scale=1, offset=0):
        super().__init__(name, unit_label, scale, offset)
        self.register_msb = int(register_msb)
        self.register_lsb = int(register_lsb)
        self._unscaled_value_msb = None
        self._unscaled_value_lsb = None

    def get_registers(self) -> bytes:
        return bytes([self.register_msb, self.register_lsb])

    def get_register(self) -> int:
        return self.register_lsb

    def get_unscaled_value(self):
        value = None
        if self._unscaled_value_msb is not None and self._unscaled_value_lsb is not None:
            value = (self._unscaled_value_msb << 8) + self._unscaled_value_lsb
        elif self._unscaled_value_msb is None and self._unscaled_value_lsb is not None:
            value = self._unscaled_value_lsb
        elif self._unscaled_value_lsb is None and self._unscaled_value_msb is not None:
            value = self._unscaled_value_msb << 8
        return value

    def update_value(self, header: bytes, frame: bytes):
        EcuParam.sanity_check(header, frame)
        self._unscaled_value_msb = EcuParam.extract_value(header, frame, self.register_msb)
        self._unscaled_value_lsb = EcuParam.extract_value(header, frame, self.register_lsb)


class EcuParamBit(EcuParam):
    def __init__(self, name, register: int, bit, unit_label="", scale=1, offset=0):
        super().__init__(name, unit_label, scale, offset)
        self.register = register
        self.bit = bit
        self.bit_value = None

    def get_registers(self) -> bytes:
        return bytes(self.get_register())

    def get_register(self) -> int:
        return self.register

    def get_unscaled_value(self):
        return self.bit_value

    def get_value(self):
        return self.bit_value

    def update_value(self, header: bytes, frame: bytes):
        EcuParam.sanity_check(header, frame)
        value = EcuParam.extract_value(header, frame, self.register)
        self.bit_value = (value >> self.bit) & 1
