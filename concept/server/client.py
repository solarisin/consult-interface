import socket
import threading
import queue
import time


class TCPClient(threading.Thread):
    def __init__(self, host='localhost', port=12345):
        super().__init__()
        self.host = host
        self.port = port
        self._data_out = queue.Queue()
        self._data_in = queue.Queue()
        self._running = threading.Event()
        self._running.set()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._receive_thread = None

    def run(self):
        try:
            self.client_socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")

            self._receive_thread = threading.Thread(target=self.receive_data)
            self._receive_thread.start()

            while self._running.is_set():
                send = bytearray()
                try:
                    q_size = self._data_out.qsize()
                    if q_size > 0:
                        for _ in range(self._data_out.qsize()):
                            send += self._data_out.get(block=False)
                        self.client_socket.sendall(send)
                    else:
                        time.sleep(0.1)
                except queue.Empty:
                    continue
                except socket.error as e:
                    print(f"Socket error sending data: {e}")
                    break
            self.stop()
            print("Client stopped")
        except socket.error as e:
            print(f"Socket error connecting to server: {e}")
            self.stop()

    def receive_data(self):
        while self._running.is_set():
            try:
                data = self.client_socket.recv(1024)
                if data:
                    for b in data:
                        self._data_in.put(b)
                else:
                    break
            except socket.timeout as e:
                print(f"Socket timeout receiving data: {e}")
                continue
            except socket.error as e:
                print(f"Socket error receiving data: {e}")
                break

    def stop(self):
        self._running.clear()
        if self.client_socket:
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.close()
            self.client_socket = None
        if self._receive_thread:
            self._receive_thread.join()

    def send_data(self, data: bytes):
        if data:
            for b in data:
                self._data_out.put(b)