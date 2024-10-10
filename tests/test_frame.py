# test frame decoding
import logging
from pathlib import Path as path
from abc import ABC
from consult_interface.ci_serial import ConsultSerial
import consult_interface.utils as ci_utils
from consult_interface import Definition as ci_def
import json

import matplotlib.pyplot as plt

logging.getLogger().propagate = True
log = logging.getLogger(__name__)
frame_log = logging.getLogger("frame_log")

def show_plot(array, title):
    import matplotlib.pyplot as plt
    plt.plot(array)
    plt.title(title)
    plt.show()


class MockConsultSerial(ConsultSerial):
    def __init__(self, port: str, file: path):
        super().__init__(port)
        self._Bps = self._baud / 8 # 9600 / 8 = 1200 Bytes per second
        self._file = file

    def _open(self):
        pass

    def _close(self):
        pass

    def _write(self, data) -> int | None:
        return len(data)

    def _read(self, size: int) -> bytes:
        return b'\x00' * size

    def is_connected(self):
        return True

def test_decode_response(caplog, data_registry):
    caplog.set_level(logging.DEBUG)
    log.debug("Test decoding of response frame")
    data_entry_id = "test_1"

    test_data = data_registry.get(data_entry_id)
    if test_data is None:
        log.error(f"Data entry '{data_entry_id}' not found")
        assert False

    log.debug(f"  Sent Command: {test_data.command.hex(' ').upper()}")
    log.debug(f"  Capture File: {test_data.capture_file}")

    # determine which command was sent - it should be register param
    if test_data.command[0] == ci_def.cmd_ecu_part_number:
        log.debug("Command: Read ECU Part Number - incorrect for this test")
        assert False
    elif test_data.command[0] != ci_def.cmd_register_param:
        log.error(f"Unknown cmd id in first byte sent: '{test_data.command[0]}'")
        assert False

    assert test_data.command[-1] == ci_def.start_stream

    # use the command-to-params function to determine the parameters of the command
    ecu_params = ci_utils.command_to_params(test_data.command)
    log.debug(f"Command: Register Parameters - {len(ecu_params)} total")
    for param in ecu_params:
        param.enable()
        log.debug(f"  Param: {param.name} - {param.get_registers().hex(' ').upper()}")

    # remove the start stream byte from the command sent
    command_sent = test_data.command.rstrip(b'\xF0')

    with (open(test_data.capture_file, 'rb') as file):
        # read until we find the frame start flag (0xFF), this is the response header (also contains error checks)
        header = bytearray()
        while byte := file.read(1):
            if len(byte) == 0:
                raise ValueError("End of file reached before command check complete")
            if byte == b'\xFF':
                file.seek(-1, 1)
                break
            header.append(byte[0])

        log.debug(f"Command sent    : {command_sent.hex(' ').upper()}")
        log.debug(f"Response header : {header.hex(' ').upper()}")

        # At this point we should know this is a response to the parameter stream command - so it should contain
        #  an error check byte followed by each parameter value in order
        assert len(command_sent) == len(header)
        for i in range(len(command_sent)):
            if i % 2 == 0:
                assert command_sent[i] == ci_utils.invert_byte(header[i])[0]
            else:
                assert command_sent[i] == header[i]

        # the next byte should be 0xFF
        frame_start = file.read(1)
        assert frame_start == b'\xFF'

        # The next byte is the size of the data in the frame
        frame_data_size_byte = file.read(1)
        assert len(frame_data_size_byte) == 1
        # add the length of the header delimiter byte and size byte for the total frame size
        frame_size = frame_data_size_byte[0] + 2

        log.debug(f"Frame Size: {frame_size}")

        # Read the entirety of the first frame
        file.seek(-2, 1)
        first_frame = file.read(frame_size)
        assert(len(first_frame) == frame_size)
        frame_log.debug(f" 1: {first_frame.hex(' ').upper()}")

        # TODO - values are incorrect
        j_dict = {
            "header": header.hex(' ').upper(),
            "frame": first_frame.hex(' ').upper(),
            "frame_index": 1,
            "parameters": []
        }
        for p in ci_def.get_enabled_parameters():
            p.update_value(header, first_frame)
            j_dict["parameters"].append(p.to_dict())

        out_file_path = path("output/first_frame.json").absolute()
        out_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file_path, 'w') as f_out:
            f_out.write(json.dumps(j_dict, indent=2))

        # read the rest of the frames in the file
        n = 1
        plot_dict = {}
        for p in ci_def.get_enabled_parameters():
            plot_dict[p.name] = []
        plot_dict["RPM Sum"] = []

        while frame := file.read(frame_size):
            n+=1
            if len(frame) != frame_size:
                log.debug(f"End of file reached after {n} frames")
                break
            if n < 100:
                frame_log.debug(f"{n:2}: {frame.hex(' ').upper()}")
            if 12500 < n < 17500:
                rpm_value = 0
                rpm_ref_value = 0
                for p in ci_def.get_enabled_parameters():
                    p.update_value(header, frame)
                    plot_dict[p.name].append(p.get_value())
                    if p.param_id == ci_utils.ParamID.ENGINE_SPEED_HR:
                        rpm_value = p.get_value()
                    if p.param_id == ci_utils.ParamID.ENGINE_SPEED_LR:
                        rpm_ref_value = p.get_value()
                plot_dict["RPM Sum"].append(rpm_value + rpm_ref_value)
                
        for name, values in plot_dict.items():
            show_plot(values, name)
    # consult = MockConsultSerial(port, response_playback_file)
    # consult.initialize_ecu()
    # consult.read_ecu_part_number()
    # assert True