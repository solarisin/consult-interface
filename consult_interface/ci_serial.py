from abc import ABC, abstractmethod
from typing import Callable

import serial
import threading

from .import utils as utils
from .utils import Definition as Definition


class InitializeFailedError(ValueError):
    pass

# base class for communication to the nissan consult UART interface over a usb serial connection
class ConsultSerial(ABC):
    def __init__(self, port: str):
        self._port = port
        self._baud = 9600
        self._initialized = False

    @abstractmethod
    def _open(self):
        pass

    @abstractmethod
    def _close(self):
        pass

    @abstractmethod
    def _write(self, data):
        pass

    @abstractmethod
    def _read(self, size: int):
        pass

    # 'public' methods

    @abstractmethod
    def is_connected(self):
        pass

    def initialize_ecu(self):
        if not self.is_connected():
            self._open()

        # Write the init command bytes to the serial port and wait for the inverse response
        self._write(Definition.init)
        init_response = utils.invert_bytes(Definition.init)
        response = self._read(len(init_response))
        if not response == init_response:
            raise InitializeFailedError(f"Unexpected init response: {response.hex()}")
        self._initialized = True
        return True

    def read_ecu_part_number(port: serial.Serial):
        ecu_part_number_cmd = b'\xD0'
        ecu_part_number_ack = invert_bytes(ecu_part_number_cmd)
        cmd_delimiter = b'\xF0'
        cmd_stop = b'\x30'
        cmd_stop_ack = invert_bytes(cmd_stop)
        port.write(ecu_part_number_cmd + cmd_delimiter)

        ack = port.read(1)
        if not ack == ecu_part_number_ack:
            raise InvalidAckError(
                f"Received unexpected acknowledge byte '{ack.hex(' ')}', expected '{ecu_part_number_ack.hex(' ')}'")
        port.write(cmd_stop)
        data = port.read(24)
        process_frame(ecu_part_number_cmd, data)
        stop_ack = port.read(1)
        if stop_ack != cmd_stop_ack:
            raise InvalidAckError(f"Unexpected stop ack received: {stop_ack.hex(' ')}")

    def stop_stream(self):
        """
        Send the ECU a command to stop streaming data
        """
        self._write(Definition.stop_stream)


# Thread class for reading ECU parameter frames from the serial port
class ReadParamFramesThread(threading.Thread):
    def __init__(self, port: serial.Serial, frame_bytes: int, process_frame: Callable[[bytes], None]):
        threading.Thread.__init__(self)
        self._frame_size = frame_bytes
        self._port = port
        self._running = False
        self.process_frame = process_frame

    def run(self):
        def process_read(frame):
            return self.process_frame(frame)

        port_opened = False
        if not self._port.open():
            self._port.open()
            port_opened = True

        self._running = True
        while self._running:
            if self._port.in_waiting > self._frame_size:
                read_bytes = self._port.read(self._frame_size)
                if read_bytes:
                    process_read(read_bytes)

        if port_opened:
            self._port.close()

    def stop(self):
        self._running = False


# Implementation of the ConsultSerial class for the actual serial communication
def _process_frame(frame: bytes):
    print(f'Processing frame: {frame.hex()}')


class ConsultSerialImpl(ConsultSerial):
    def __init__(self, port: str):
        super().__init__(port)
        self._serial = serial.Serial(self._port, self._baud, timeout=None, xonxoff=False, rtscts=False, dsrdtr=False)
        ReadParamFramesThread(self._serial, 11, _process_frame).start()

    def _open(self):
        if not self._serial.is_open:
            self._serial.open()

    def _close(self):
        # noinspection PyBroadException
        try:
            self.stop_stream()
        except:
            pass # We are shutting down, so we don't care if this fails
        self._serial.close()

    def _write(self, data) -> int | None:
        return self._serial.write(data)

    def _read(self, size: int) -> bytes:
        return self._serial.read(size)

    def is_connected(self):
        return self._serial.is_open


def create(port: str, mock=False) -> ConsultSerial:
    if mock:
        raise NotImplementedError("Mock serial interface not implemented")
    else:
        return ConsultSerialImpl(port)


# scrap mock for now
# class ConsultSerialMock(ConsultSerial):
#     def __init__(self):
#         super().__init__("mock")
#         self._initialized = False
#         self._input_queue = queue.Queue()
#         self._output_queue = queue.Queue()
#         self._is_streaming = False
#
#     def _open(self):
#         threading.Thread(target=self._read_thread, name="serial mock read thread").start()
#         threading.Thread(target=self._write_thread, name="serial mock write thread").start()
#         pass
#
#     def _close(self):
#         self._input_buffer.join()
#         self._output_buffer.join()
#
#     def _read_thread(self):
#         input_buffer = bytearray()
#         while True:
#             data = self._input_buffer.get()
#
#
#     def _write_thread(self):
#         pass
#
#     def _write(self, data):
#         # data being written to the mocked ecu's input buffer (append until a recognized command is found)
#         self._input_buffer += data
#
#         if not self._initialized:
#             # process the input buffer from start to end looking for the initialization command (0xFF, 0xFF, 0xEF)
#             self._initialized, self._input_buffer = ci.utils.scan_match(self._input_buffer, ci.Definition.init)
#
#
#         if not self._is_streaming:
#
#         # now look for the configuration message which contains the parameter delimiter (0x5A) immediately
#         # followed by a byte identifying the command. Stop looking when the start_stream command (0xF0) is found
#         for i in range(len(self._input_buffer)):
#             if self._input_buffer[i] == ci.Definition.register_param:
#                 if i + 1 < len(self._input_buffer):
#                     command = self._input_buffer[i + 1]
#                     self._input_buffer = self._input_buffer[i + 2:]
#                     self._stored_commands(command)
#                     break
#
#
#
#         for i in range(len(self._input_buffer)):
#             if self._input_buffer[i] == ci.Definition.register_param:
#                 if i + 1 < len(self._input_buffer):
#                     command = self._input_buffer[i + 1]
#                     self._input_buffer = self._input_buffer[i + 2:]
#                     self._process_command(command)
#                     break
#
#     def _read(self):
#         # data being read from the mocked ecu's output buffer
#         pass

