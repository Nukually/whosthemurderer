import json
import socket
import threading

from PyQt5 import QtCore


class NetworkClient(QtCore.QObject):
    connected = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()
    message_received = QtCore.pyqtSignal(dict)
    error = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._socket = None
        self._thread = None
        self._lock = threading.Lock()

    def connect_to_host(self, host, port, display_name, is_host=False):
        if self._socket:
            return False
        try:
            sock = socket.create_connection((host, port), timeout=5)
        except OSError as exc:
            self.error.emit(str(exc))
            return False
        self._socket = sock
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        self.send({"type": "connect", "display_name": display_name, "is_host": is_host})
        self.connected.emit()
        return True

    def send(self, message):
        if not self._socket:
            return
        raw = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        with self._lock:
            try:
                self._socket.sendall(raw)
            except OSError:
                pass

    def close(self):
        if not self._socket:
            return
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._socket.close()
        except OSError:
            pass
        self._socket = None
        self.disconnected.emit()

    def _read_loop(self):
        buffer = b""
        while self._socket:
            try:
                data = self._socket.recv(4096)
            except OSError:
                break
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line:
                    continue
                try:
                    message = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                self.message_received.emit(message)
        self.close()
