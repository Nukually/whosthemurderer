import json
import os
import random
import threading


class ScriptStore:
    def __init__(self, scripts_path):
        self._scripts_path = scripts_path
        self._scripts = {}
        self._load_scripts()

    def _load_scripts(self):
        if not os.path.isdir(self._scripts_path):
            return
        for name in os.listdir(self._scripts_path):
            if not name.endswith(".json"):
                continue
            path = os.path.join(self._scripts_path, name)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue
            script_id = data.get("id")
            if not script_id:
                continue
            self._scripts[script_id] = data

    def list_scripts(self):
        output = []
        for script_id, data in sorted(self._scripts.items()):
            output.append({
                "id": script_id,
                "title": data.get("title", ""),
                "summary": data.get("summary", ""),
                "role_count": len(data.get("roles", [])),
            })
        return output

    def get_script(self, script_id):
        return self._scripts.get(script_id)


class GameRoom:
    def __init__(self, script_store):
        self._lock = threading.Lock()
        self._script_store = script_store
        self._players = {}
        self._next_player_id = 1
        self._phase = "Idle"
        self._script_id = None
        self._player_count = 4

    def add_player(self, display_name, is_host):
        with self._lock:
            player_id = self._next_player_id
            self._next_player_id += 1
            self._players[player_id] = {
                "player_id": player_id,
                "display_name": display_name or f"Player {player_id}",
                "role_id": None,
                "is_host": is_host,
                "connected": True,
            }
            return player_id

    def is_host(self, player_id):
        with self._lock:
            player = self._players.get(player_id)
            return bool(player and player.get("is_host"))

    def remove_player(self, player_id):
        with self._lock:
            player = self._players.get(player_id)
            if player:
                player["connected"] = False

    def set_name(self, player_id, display_name):
        with self._lock:
            player = self._players.get(player_id)
            if player and display_name:
                player["display_name"] = display_name

    def set_player_count(self, player_count):
        with self._lock:
            self._player_count = player_count

    def select_script(self, script_id):
        with self._lock:
            script = self._script_store.get_script(script_id)
            if not script:
                return False
            self._script_id = script_id
            self._phase = "Configuring"
            return True

    def assign_roles(self):
        with self._lock:
            script = self._script_store.get_script(self._script_id)
            if not script:
                return None, "No script selected"
            roles = list(script.get("roles", []))
            connected_players = [
                player for player in self._players.values() if player["connected"]
            ]
            if len(connected_players) < self._player_count:
                return None, "Not enough players connected"
            if len(roles) < self._player_count:
                return None, "Not enough roles in script"
            random.shuffle(roles)
            assigned = {}
            for index, player in enumerate(connected_players[: self._player_count]):
                role = roles[index]
                player["role_id"] = role.get("id")
                assigned[player["player_id"]] = role
            self._phase = "Reading"
            return assigned, None

    def get_state(self):
        with self._lock:
            script = self._script_store.get_script(self._script_id)
            script_info = None
            if script:
                script_info = {
                    "id": script.get("id"),
                    "title": script.get("title", ""),
                    "summary": script.get("summary", ""),
                }
            return {
                "phase": self._phase,
                "player_count": self._player_count,
                "players": list(self._players.values()),
                "script": script_info,
            }

    def list_scripts(self):
        return self._script_store.list_scripts()
