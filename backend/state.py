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
        self._revealed_clues = {}
        self._votes = {}
        self._result = None

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
                "current_vote": None,
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
            if self._phase not in ("Idle", "Configuring"):
                return False, "Name changes are locked after the game starts"
            player = self._players.get(player_id)
            if player and display_name:
                player["display_name"] = display_name
                return True, None
            return False, "Invalid player name"

    def set_player_count(self, player_count):
        with self._lock:
            self._player_count = player_count

    def select_script(self, script_id):
        with self._lock:
            script = self._script_store.get_script(script_id)
            if not script:
                return False
            self._script_id = script_id
            self._reset_round()
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
            self._reset_round()
            random.shuffle(roles)
            assigned = {}
            for index, player in enumerate(connected_players[: self._player_count]):
                role = roles[index]
                player["role_id"] = role.get("id")
                role_payload = self._build_role_payload(role, player.get("display_name", ""))
                assigned[player["player_id"]] = role_payload
            self._phase = "Reading"
            return assigned, None

    def advance_phase(self):
        with self._lock:
            transitions = {
                "Reading": "Investigation",
                "Investigation": "Voting",
                "Voting": "ResultReview",
                "ResultReview": "Archived",
                "Archived": "Configuring" if self._script_id else "Idle",
            }
            next_phase = transitions.get(self._phase)
            if not next_phase:
                return False, "Cannot advance phase"
            if next_phase == "Voting":
                self._reset_votes()
            if next_phase == "ResultReview":
                self._result = self._build_result()
            self._phase = next_phase
            return True, None

    def reset_game(self):
        with self._lock:
            self._reset_round()
            self._phase = "Configuring" if self._script_id else "Idle"
            return True

    def reveal_clue(self, clue_id):
        with self._lock:
            if self._phase != "Investigation":
                return None, "Not in investigation phase"
            script = self._script_store.get_script(self._script_id)
            if not script:
                return None, "No script selected"
            for clue in script.get("clues", []):
                if clue.get("id") == clue_id:
                    clue_data = {
                        "id": clue.get("id"),
                        "name": clue.get("name", ""),
                        "type": clue.get("type", "normal"),
                        "content": clue.get("content", ""),
                    }
                    self._revealed_clues[clue_id] = clue_data
                    return clue_data, None
            return None, "Invalid clue"

    def submit_vote(self, player_id, target_id):
        with self._lock:
            if self._phase != "Voting":
                return None, "Not in voting phase"
            if player_id not in self._players:
                return None, "Unknown player"
            if target_id not in self._players:
                return None, "Invalid vote target"
            self._votes[player_id] = target_id
            self._players[player_id]["current_vote"] = target_id
            return self._build_vote_summary(), None

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
            clues = self._build_clue_overview(script) if script else []
            revealed_clues = list(self._revealed_clues.values())
            role_intros = self._build_role_intros(script) if script else []
            votes = None
            if self._phase in ("Voting", "ResultReview", "Archived"):
                votes = self._build_vote_summary()
            result = self._result if self._phase in ("ResultReview", "Archived") else None
            return {
                "phase": self._phase,
                "player_count": self._player_count,
                "players": list(self._players.values()),
                "script": script_info,
                "role_intros": role_intros,
                "clues": clues,
                "revealed_clues": revealed_clues,
                "votes": votes,
                "result": result,
            }

    def list_scripts(self):
        return self._script_store.list_scripts()

    def _reset_round(self):
        self._revealed_clues = {}
        self._votes = {}
        self._result = None
        for player in self._players.values():
            player["role_id"] = None
            player["current_vote"] = None

    def _reset_votes(self):
        self._votes = {}
        for player in self._players.values():
            player["current_vote"] = None

    def _build_vote_summary(self):
        connected_players = [
            player for player in self._players.values() if player["connected"]
        ]
        counts = {}
        for target_id in self._votes.values():
            key = str(target_id)
            counts[key] = counts.get(key, 0) + 1
        return {
            "submitted": len(self._votes),
            "eligible": len(connected_players),
            "counts": counts,
        }

    def _build_clue_overview(self, script):
        revealed = set(self._revealed_clues.keys())
        output = []
        for clue in script.get("clues", []):
            clue_id = clue.get("id")
            output.append({
                "id": clue_id,
                "name": clue.get("name", ""),
                "type": clue.get("type", "normal"),
                "revealed": clue_id in revealed,
            })
        return output

    def _build_result(self):
        script = self._script_store.get_script(self._script_id)
        if not script:
            return None
        return {
            "truth": script.get("truth", ""),
            "events": script.get("events", []),
            "votes": self._build_vote_summary(),
        }

    def _build_role_payload(self, role, display_name):
        role_payload = dict(role)
        original_name = role_payload.get("name", "")
        role_payload["name"] = display_name or original_name
        role_payload["intro"] = self._replace_role_name(
            role_payload.get("intro", ""), original_name, role_payload["name"]
        )
        role_payload["story"] = self._replace_role_name(
            role_payload.get("story", ""), original_name, role_payload["name"]
        )
        return role_payload

    def _replace_role_name(self, text, original_name, display_name):
        if not text or not original_name or not display_name:
            return text
        return text.replace(original_name, display_name)

    def _build_role_intros(self, script):
        roles = script.get("roles", []) if script else []
        output = []
        for role in roles:
            output.append({
                "id": role.get("id"),
                "name": role.get("name", ""),
                "intro": role.get("intro", ""),
            })
        return output
