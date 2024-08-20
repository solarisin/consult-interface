import socket
import threading
import queue
import logging
import time


class TCPServer(threading.Thread):
    def __init__(self, host='localhost', port=12345):
        super().__init__()
        self.host = host
        self.port = port
        self._data_out = queue.Queue()
        self._data_in = queue.Queue()
        self._running = threading.Event()
        self._running.set()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        self.client_socket = None

    def run(self):
        logging.info(f"Server started on {self.host}:{self.port}")
        while self._running.is_set():
            try:
                self.client_socket, client_address = self.server_socket.accept()
                logging.info(f"Connection from {client_address}")

                receive_thread = threading.Thread(target=self.receive_data)
                receive_thread.start()

                while self._running.is_set() and self.client_socket:
                    try:
                        data = self._data_out.get(timeout=1)
                        if self.client_socket:
                            self.client_socket.sendall(data)
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logging.error(f"Error sending data: {e}")
                        break
                logging.info(f"Client {client_address} disconnected")
            except socket.error as e:
                logging.error(f"Error accepting connection: {e}")

        if self.client_socket:
            self.client_socket.close()
        self.client_socket = None

        logging.info("Server stopped")

    def receive_data(self):
        while self._running.is_set() and self.client_socket:
            try:
                data = self.client_socket.recv(1024)
                if data:
                    for b in data:
                        self._data_in.put(b)
                else:
                    logging.info("Client disconnected")
                    break
            except Exception as e:
                logging.error(f"Error receiving data: {e}")
                break
        self.client_socket = None  # Ensure the client socket is reset

    def stop(self):
        self._running.clear()
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None
        self.server_socket.close()

    def send_data(self, data: bytes):
        if not self.client_socket:
            if self._data_out.qsize() > 0:
                self._data_out = queue.Queue()
            return
        self._data_out.put(data)

    def read_data(self, num_bytes=1) -> bytes | None:
        if not self.client_socket:
            if self._data_in.qsize() > 0:
                self._data_in = queue.Queue()
            return None
        try:
            result = bytearray()
            while len(result) < num_bytes:
                result.append(self._data_in.get(timeout=1))
            return bytes(result)
        except queue.Empty:
            return None


def main(host: str, port: int):
    logging.basicConfig(level=logging.INFO)
    server = TCPServer(host=host, port=port)
    server.start()

    try:
        response_repeat = bytearray()
        while True:
            try:
                if len(response_repeat) > 0:
                    # logging.info(f"Sending response repeat: {response_repeat.hex(' ')}")
                    server.send_data(response_repeat)
                    time.sleep(0.01)
                    continue
                received_data = server.read_data(3)
                if received_data:
                    logging.info(f"Received data: {received_data.hex(' ')}")
                    if received_data == b'\x5A\x0D\xF0':
                        response = b'\xA5\x0D\xFF\x01\x11'
                        response_repeat = b'\xFF\x01\x11'
                        logging.info(f"Sending response: {response.hex(' ')}")
                        server.send_data(response)
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        server.stop()
        server.join()


if __name__ == "__main__":
    def parse_args():
        import argparse
        parser = argparse.ArgumentParser(description="Run a TCP server")
        parser.add_argument("--host", type=str, default='localhost', help="The host to bind to")
        parser.add_argument("--port", type=int, default=12345, help="The port to bind to")
        return parser.parse_args()
    args = parse_args()
    main(args.host, args.port)