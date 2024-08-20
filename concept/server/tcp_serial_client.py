import queue
import time

from concept.server.client import TCPClient


class TCPSerial:
    """
    A class that simulates a serial port over TCP.
    """
    def __init__(self, host='localhost', port=12345):
        self.client = TCPClient(host, port)
        self._data_out = self.client._data_out
        self._data_in = self.client._data_in

    def open(self):
        self.client.start()

    def close(self):
        self.client.stop()
        self.client.join()

    def write(self, data: bytes):
        self._data_out.put(data)

    def read(self, size=1):
        data = bytearray()
        while len(data) < size:
            try:
                chunk = self._data_in.get(block=False)
                data.append(chunk)
            except queue.Empty:
                break
        return bytes(data)

    def read_all(self):
        """
        Read all bytes currently available in the buffer
        """
        return self.read(self.in_waiting)

    @property
    def in_waiting(self):
        """
        Return the number of bytes currently in the buffer
        """
        return self._data_in.qsize()


if __name__ == "__main__":
    tcp_serial = TCPSerial(host='localhost', port=12345)
    tcp_serial.open()

    tcp_serial.write(b'\x5A\x0D\xF0')
    time.sleep(.1)
    try:
        while True:
            received_data = tcp_serial.read(3)
            size = len(received_data)
            time.sleep(.001)
            if received_data:
                if size == 3:
                    print(f"Received {size} byte(s) of data: {received_data.hex(' ')}")
                else:
                    print(f"ERROR: Received {size} bytes of data: {received_data.hex(' ')}")
    except KeyboardInterrupt:
        print("Exiting")

    tcp_serial.close()
