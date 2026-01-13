import socketserver
import threading

from backend.protocol import decode_message, send_message
from backend.state import GameRoom, ScriptStore

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5000
MIN_PLAYER_COUNT = 4
MAX_PLAYER_COUNT = 6


class GameRequestHandler(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup()
        self.player_id = None

    def handle(self):
        while True:
            raw_line = self.rfile.readline()
            if not raw_line:
                break
            try:
                message = decode_message(raw_line.decode("utf-8").strip())
            except Exception:
                continue
            if not message:
                continue
            self.server.game_server.handle_message(self, message)

    def finish(self):
        if self.player_id:
            self.server.game_server.remove_session(self.player_id)
        super().finish()

    def send(self, message):
        try:
            send_message(self.wfile, message)
        except Exception:
            pass


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class GameServer:
    def __init__(self, host, port, scripts_path):
        self._host = host
        self._port = port
        self._scripts = ScriptStore(scripts_path)
        self._room = GameRoom(self._scripts)
        self._lock = threading.Lock()
        self._sessions = {}
        self._server = None
        self._thread = None

    def start(self):
        if self._server:
            return
        self._server = ThreadedTCPServer((self._host, self._port), GameRequestHandler)
        self._server.game_server = self
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None

    def handle_message(self, handler, message):
        message_type = message.get("type")
        if message_type == "connect":
            display_name = message.get("display_name", "")
            is_host = bool(message.get("is_host"))
            player_id = self._room.add_player(display_name, is_host)
            handler.player_id = player_id
            with self._lock:
                self._sessions[player_id] = handler
            handler.send({"type": "welcome", "player_id": player_id, "is_host": is_host})
            handler.send({"type": "scripts", "scripts": self._room.list_scripts()})
            self.broadcast_state()
            return

        if handler.player_id is None:
            handler.send({"type": "error", "message": "Not connected"})
            return

        if message_type == "set_name":
            self._room.set_name(handler.player_id, message.get("display_name", ""))
            self.broadcast_state()
            return

        if message_type == "request_scripts":
            handler.send({"type": "scripts", "scripts": self._room.list_scripts()})
            return

        if message_type == "select_script":
            if not self._room.is_host(handler.player_id):
                handler.send({"type": "error", "message": "Host only"})
                return
            script_id = message.get("script_id")
            if not script_id or not self._room.select_script(script_id):
                handler.send({"type": "error", "message": "Invalid script"})
                return
            self.broadcast_state()
            return

        if message_type == "set_player_count":
            if not self._room.is_host(handler.player_id):
                handler.send({"type": "error", "message": "Host only"})
                return
            try:
                player_count = int(message.get("player_count"))
            except (TypeError, ValueError):
                handler.send({"type": "error", "message": "Invalid player count"})
                return
            if player_count < MIN_PLAYER_COUNT or player_count > MAX_PLAYER_COUNT:
                handler.send({"type": "error", "message": "Player count must be 4-6"})
                return
            self._room.set_player_count(player_count)
            self.broadcast_state()
            return

        if message_type == "assign_roles":
            if not self._room.is_host(handler.player_id):
                handler.send({"type": "error", "message": "Host only"})
                return
            assigned, error = self._room.assign_roles()
            if error:
                handler.send({"type": "error", "message": error})
                return
            for player_id, role in assigned.items():
                session = self._sessions.get(player_id)
                if session:
                    session.send({"type": "role_assigned", "role": role})
            self.broadcast_state()
            return

        if message_type == "ping":
            handler.send({"type": "pong"})
            return

    def broadcast_state(self):
        state = self._room.get_state()
        message = {"type": "state", "state": state}
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            session.send(message)

    def remove_session(self, player_id):
        self._room.remove_player(player_id)
        with self._lock:
            self._sessions.pop(player_id, None)
        self.broadcast_state()
