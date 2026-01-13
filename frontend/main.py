import os
import socket
import sys

from PyQt5 import QtCore, QtWidgets

from backend.server import GameServer, DEFAULT_HOST, DEFAULT_PORT
from frontend.client_network import NetworkClient


def get_local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip_address = sock.getsockname()[0]
        sock.close()
        return ip_address
    except OSError:
        return "127.0.0.1"


def get_scripts_path():
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, "data", "scripts")


class StartPage(QtWidgets.QWidget):
    host_requested = QtCore.pyqtSignal(str, int)
    client_requested = QtCore.pyqtSignal(str, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(20)

        host_group = QtWidgets.QGroupBox("Host (start server)")
        host_layout = QtWidgets.QFormLayout(host_group)
        self.host_ip_label = QtWidgets.QLabel(get_local_ip())
        self.host_name_input = QtWidgets.QLineEdit()
        self.host_name_input.setPlaceholderText("Host name")
        self.host_port_input = QtWidgets.QSpinBox()
        self.host_port_input.setRange(1, 65535)
        self.host_port_input.setValue(DEFAULT_PORT)
        host_button = QtWidgets.QPushButton("Start host")
        host_button.clicked.connect(self._on_host_clicked)
        host_layout.addRow("Local IP", self.host_ip_label)
        host_layout.addRow("Name", self.host_name_input)
        host_layout.addRow("Port", self.host_port_input)
        host_layout.addRow(host_button)

        client_group = QtWidgets.QGroupBox("Client (connect to host)")
        client_layout = QtWidgets.QFormLayout(client_group)
        self.client_name_input = QtWidgets.QLineEdit()
        self.client_name_input.setPlaceholderText("Player name")
        self.client_host_input = QtWidgets.QLineEdit()
        self.client_host_input.setPlaceholderText("Host IP")
        self.client_host_input.setText("127.0.0.1")
        self.client_port_input = QtWidgets.QSpinBox()
        self.client_port_input.setRange(1, 65535)
        self.client_port_input.setValue(DEFAULT_PORT)
        client_button = QtWidgets.QPushButton("Connect")
        client_button.clicked.connect(self._on_client_clicked)
        client_layout.addRow("Name", self.client_name_input)
        client_layout.addRow("Host IP", self.client_host_input)
        client_layout.addRow("Port", self.client_port_input)
        client_layout.addRow(client_button)

        layout.addWidget(host_group)
        layout.addWidget(client_group)
        layout.addStretch(1)

    def _on_host_clicked(self):
        name = self.host_name_input.text().strip() or "Host"
        port = int(self.host_port_input.value())
        self.host_requested.emit(name, port)

    def _on_client_clicked(self):
        name = self.client_name_input.text().strip() or "Player"
        host = self.client_host_input.text().strip() or "127.0.0.1"
        port = int(self.client_port_input.value())
        self.client_requested.emit(host, port, name)


class MainPage(QtWidgets.QWidget):
    select_script = QtCore.pyqtSignal(str)
    set_player_count = QtCore.pyqtSignal(int)
    assign_roles = QtCore.pyqtSignal()
    rename_requested = QtCore.pyqtSignal(str)
    advance_phase = QtCore.pyqtSignal()
    reset_game = QtCore.pyqtSignal()
    request_clue = QtCore.pyqtSignal(str)
    submit_vote = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scripts = {}
        self._player_id = None
        self._name_dirty = False
        self._clues = []
        self._revealed_clues = {}
        self._current_vote = None
        self._role_data = {}
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        status_layout = QtWidgets.QHBoxLayout()
        self.phase_label = QtWidgets.QLabel("Phase: Idle")
        self.script_label = QtWidgets.QLabel("Script: -")
        self.count_label = QtWidgets.QLabel("Players: 0")
        status_layout.addWidget(self.phase_label)
        status_layout.addWidget(self.script_label)
        status_layout.addWidget(self.count_label)
        status_layout.addStretch(1)
        layout.addLayout(status_layout)

        body_layout = QtWidgets.QHBoxLayout()
        left_layout = QtWidgets.QVBoxLayout()
        self.players_list = QtWidgets.QListWidget()
        self.players_list.setMinimumWidth(220)
        left_layout.addWidget(self.players_list)

        role_group = QtWidgets.QGroupBox("Your role")
        role_layout = QtWidgets.QVBoxLayout(role_group)
        self.role_name_label = QtWidgets.QLabel("Role: -")
        self.view_role_button = QtWidgets.QPushButton("View role script")
        self.view_role_button.clicked.connect(self._on_view_role)
        role_layout.addWidget(self.role_name_label)
        role_layout.addWidget(self.view_role_button)
        left_layout.addWidget(role_group)

        intro_group = QtWidgets.QGroupBox("Role introductions")
        intro_layout = QtWidgets.QVBoxLayout(intro_group)
        self.role_intro_list = QtWidgets.QListWidget()
        intro_layout.addWidget(self.role_intro_list)
        left_layout.addWidget(intro_group)

        name_group = QtWidgets.QGroupBox("Player")
        name_layout = QtWidgets.QFormLayout(name_group)
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Your name")
        self.name_input.textEdited.connect(self._on_name_edited)
        self.name_button = QtWidgets.QPushButton("Update name")
        self.name_button.clicked.connect(self._on_update_name)
        name_layout.addRow("Your name", self.name_input)
        name_layout.addRow(self.name_button)
        left_layout.addWidget(name_group)
        left_layout.addStretch(1)
        body_layout.addLayout(left_layout)

        self.phase_stack = QtWidgets.QStackedWidget()

        reading_page = QtWidgets.QWidget()
        role_layout = QtWidgets.QVBoxLayout(reading_page)
        self.role_title = QtWidgets.QLabel("Role: -")
        self.role_intro = QtWidgets.QLabel("")
        self.role_story = QtWidgets.QTextEdit()
        self.role_story.setReadOnly(True)
        role_layout.addWidget(self.role_title)
        role_layout.addWidget(self.role_intro)
        role_layout.addWidget(self.role_story)
        self.phase_stack.addWidget(reading_page)

        investigation_page = QtWidgets.QWidget()
        investigation_layout = QtWidgets.QHBoxLayout(investigation_page)
        clue_list_layout = QtWidgets.QVBoxLayout()
        self.clue_list = QtWidgets.QListWidget()
        self.clue_list.currentItemChanged.connect(self._on_clue_selected)
        self.reveal_clue_button = QtWidgets.QPushButton("Reveal selected")
        self.reveal_clue_button.clicked.connect(self._on_reveal_clue)
        clue_list_layout.addWidget(self.clue_list)
        clue_list_layout.addWidget(self.reveal_clue_button)
        self.clue_detail = QtWidgets.QTextEdit()
        self.clue_detail.setReadOnly(True)
        investigation_layout.addLayout(clue_list_layout)
        investigation_layout.addWidget(self.clue_detail)
        self.phase_stack.addWidget(investigation_page)

        voting_page = QtWidgets.QWidget()
        voting_layout = QtWidgets.QHBoxLayout(voting_page)
        vote_list_layout = QtWidgets.QVBoxLayout()
        self.vote_list = QtWidgets.QListWidget()
        self.vote_button = QtWidgets.QPushButton("Submit vote")
        self.vote_button.clicked.connect(self._on_submit_vote)
        self.vote_status = QtWidgets.QLabel("Votes: 0/0")
        vote_list_layout.addWidget(self.vote_list)
        vote_list_layout.addWidget(self.vote_button)
        vote_list_layout.addWidget(self.vote_status)
        self.vote_results = QtWidgets.QListWidget()
        voting_layout.addLayout(vote_list_layout)
        voting_layout.addWidget(self.vote_results)
        self.phase_stack.addWidget(voting_page)

        result_page = QtWidgets.QWidget()
        result_layout = QtWidgets.QVBoxLayout(result_page)
        self.truth_text = QtWidgets.QTextEdit()
        self.truth_text.setReadOnly(True)
        self.events_list = QtWidgets.QListWidget()
        self.result_votes = QtWidgets.QListWidget()
        result_layout.addWidget(QtWidgets.QLabel("Truth"))
        result_layout.addWidget(self.truth_text)
        result_layout.addWidget(QtWidgets.QLabel("Events"))
        result_layout.addWidget(self.events_list)
        result_layout.addWidget(QtWidgets.QLabel("Votes"))
        result_layout.addWidget(self.result_votes)
        self.phase_stack.addWidget(result_page)

        body_layout.addWidget(self.phase_stack)
        layout.addLayout(body_layout)

        self.host_controls = QtWidgets.QGroupBox("Host controls")
        host_layout = QtWidgets.QFormLayout(self.host_controls)
        self.script_combo = QtWidgets.QComboBox()
        self.select_script_button = QtWidgets.QPushButton("Select script")
        self.select_script_button.clicked.connect(self._on_select_script)
        self.player_count_spin = QtWidgets.QSpinBox()
        self.player_count_spin.setRange(4, 6)
        self.player_count_spin.setValue(4)
        self.player_count_spin.valueChanged.connect(self._on_player_count)
        self.assign_roles_button = QtWidgets.QPushButton("Assign roles")
        self.assign_roles_button.clicked.connect(self.assign_roles.emit)
        self.advance_phase_button = QtWidgets.QPushButton("Next phase")
        self.advance_phase_button.clicked.connect(self.advance_phase.emit)
        self.reset_game_button = QtWidgets.QPushButton("Reset game")
        self.reset_game_button.clicked.connect(self.reset_game.emit)
        host_layout.addRow("Script", self.script_combo)
        host_layout.addRow(self.select_script_button)
        host_layout.addRow("Player count", self.player_count_spin)
        host_layout.addRow(self.assign_roles_button)
        host_layout.addRow(self.advance_phase_button)
        host_layout.addRow(self.reset_game_button)
        layout.addWidget(self.host_controls)

    def set_host_mode(self, is_host):
        self.host_controls.setVisible(is_host)

    def set_player_id(self, player_id):
        self._player_id = player_id

    def update_state(self, state):
        phase = state.get("phase", "-")
        self.phase_label.setText(f"Phase: {phase}")
        script = state.get("script")
        if script:
            self.script_label.setText(f"Script: {script.get('title', '-')}")
        else:
            self.script_label.setText("Script: -")
        self.count_label.setText(f"Players: {state.get('player_count', 0)}")
        players = state.get("players", [])
        self.players_list.clear()
        for player in players:
            name = player.get("display_name") or "Player"
            role_id = player.get("role_id")
            role_text = f" (Role {role_id})" if role_id else ""
            host_flag = " [Host]" if player.get("is_host") else ""
            status = "online" if player.get("connected") else "offline"
            self.players_list.addItem(f"{name}{role_text}{host_flag} - {status}")
        self._update_name_from_players(players)
        self._update_phase_view(phase)
        self._update_role_intros(state.get("role_intros", []))
        self._update_clues(state.get("clues", []), state.get("revealed_clues", []))
        self._update_votes(state.get("votes"), players)
        self._update_result(state.get("result"), players)

    def update_scripts(self, scripts):
        self._scripts = {item["id"]: item for item in scripts}
        self.script_combo.clear()
        for script_id, item in self._scripts.items():
            title = item.get("title", script_id)
            self.script_combo.addItem(title, script_id)

    def show_role(self, role):
        self._role_data = dict(role)
        self.role_name_label.setText(f"Role: {role.get('name', '-')}")
        self.role_title.setText(f"Role: {role.get('name', '-')}")
        self.role_intro.setText(role.get("intro", ""))
        self.role_story.setPlainText(role.get("story", ""))

    def _on_view_role(self):
        if not self._role_data:
            QtWidgets.QMessageBox.information(self, "Role", "No role assigned yet.")
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Your role")
        dialog.resize(500, 400)
        layout = QtWidgets.QVBoxLayout(dialog)
        title = QtWidgets.QLabel(self._role_data.get("name", ""))
        intro = QtWidgets.QLabel(self._role_data.get("intro", ""))
        intro.setWordWrap(True)
        story = QtWidgets.QTextEdit()
        story.setReadOnly(True)
        story.setPlainText(self._role_data.get("story", ""))
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(title)
        layout.addWidget(intro)
        layout.addWidget(story)
        layout.addWidget(close_button)
        dialog.exec_()

    def _on_select_script(self):
        script_id = self.script_combo.currentData()
        if script_id:
            self.select_script.emit(script_id)

    def _on_player_count(self, value):
        self.set_player_count.emit(int(value))

    def _on_name_edited(self):
        self._name_dirty = True

    def _on_update_name(self):
        name = self.name_input.text().strip()
        if name:
            self._name_dirty = False
            self.rename_requested.emit(name)

    def _on_clue_selected(self):
        self._refresh_clue_detail()

    def _on_reveal_clue(self):
        item = self.clue_list.currentItem()
        if not item:
            return
        clue_id = item.data(QtCore.Qt.UserRole)
        if clue_id:
            self.request_clue.emit(clue_id)

    def _on_submit_vote(self):
        item = self.vote_list.currentItem()
        if not item:
            return
        target_id = item.data(QtCore.Qt.UserRole)
        if target_id is None:
            return
        self.submit_vote.emit(int(target_id))

    def _update_name_from_players(self, players):
        if not self._player_id:
            return
        for player in players:
            if player.get("player_id") == self._player_id:
                self._current_vote = player.get("current_vote")
                if not self._name_dirty:
                    self.name_input.setText(player.get("display_name", ""))
                break

    def _update_phase_view(self, phase):
        phase_index = 0
        if phase == "Investigation":
            phase_index = 1
        elif phase == "Voting":
            phase_index = 2
        elif phase in ("ResultReview", "Archived"):
            phase_index = 3
        self.phase_stack.setCurrentIndex(phase_index)
        can_rename = phase in ("Idle", "Configuring")
        self.name_input.setEnabled(can_rename)
        self.name_button.setEnabled(can_rename)

    def _update_role_intros(self, role_intros):
        self.role_intro_list.clear()
        for role in role_intros:
            name = role.get("name") or f"Role {role.get('id', '')}".strip()
            intro = role.get("intro", "")
            text = f"{name}: {intro}".strip()
            self.role_intro_list.addItem(text)

    def _update_clues(self, clues, revealed_clues):
        self._clues = clues
        self._revealed_clues = {
            clue.get("id"): clue for clue in revealed_clues if clue.get("id") is not None
        }
        self.clue_list.blockSignals(True)
        self.clue_list.clear()
        for clue in clues:
            clue_id = clue.get("id")
            name = clue.get("name") or str(clue_id)
            clue_type = clue.get("type", "normal")
            status = "revealed" if clue.get("revealed") else "hidden"
            item = QtWidgets.QListWidgetItem(f"{name} ({clue_type}) - {status}")
            item.setData(QtCore.Qt.UserRole, clue_id)
            self.clue_list.addItem(item)
        self.clue_list.blockSignals(False)
        self._refresh_clue_detail()

    def _refresh_clue_detail(self):
        item = self.clue_list.currentItem()
        if not item:
            self.clue_detail.setPlainText("Select a clue to see details.")
            return
        clue_id = item.data(QtCore.Qt.UserRole)
        clue = self._revealed_clues.get(clue_id)
        if clue:
            title = clue.get("name", "")
            content = clue.get("content", "")
            detail = f"{title}\n\n{content}".strip()
            self.clue_detail.setPlainText(detail)
        else:
            self.clue_detail.setPlainText("This clue has not been revealed yet.")

    def _update_votes(self, vote_summary, players):
        self.vote_list.blockSignals(True)
        self.vote_list.clear()
        selected_item = None
        for player in players:
            if not player.get("connected"):
                continue
            name = player.get("display_name") or "Player"
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.UserRole, player.get("player_id"))
            self.vote_list.addItem(item)
            if self._current_vote == player.get("player_id"):
                selected_item = item
        if selected_item:
            self.vote_list.setCurrentItem(selected_item)
        self.vote_list.blockSignals(False)

        if vote_summary:
            submitted = vote_summary.get("submitted", 0)
            eligible = vote_summary.get("eligible", 0)
            self.vote_status.setText(f"Votes: {submitted}/{eligible}")
            counts = vote_summary.get("counts", {})
            self.vote_results.clear()
            for player in players:
                name = player.get("display_name") or "Player"
                player_key = str(player.get("player_id"))
                count = counts.get(player_key, counts.get(player.get("player_id"), 0))
                self.vote_results.addItem(f"{name}: {count}")
        else:
            self.vote_status.setText("Votes: -")
            self.vote_results.clear()

    def _update_result(self, result, players):
        if not result:
            self.truth_text.setPlainText("")
            self.events_list.clear()
            self.result_votes.clear()
            return
        self.truth_text.setPlainText(result.get("truth", ""))
        self.events_list.clear()
        for event in result.get("events", []):
            time_text = event.get("time", "")
            content = event.get("content", "")
            label = f"{time_text} - {content}".strip(" -")
            self.events_list.addItem(label)
        self.result_votes.clear()
        vote_summary = result.get("votes", {})
        counts = vote_summary.get("counts", {})
        for player in players:
            name = player.get("display_name") or "Player"
            player_key = str(player.get("player_id"))
            count = counts.get(player_key, counts.get(player.get("player_id"), 0))
            self.result_votes.addItem(f"{name}: {count}")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Who Sthe Murder MVP")
        self.resize(900, 600)
        self._server = None
        self._client = NetworkClient()
        self._is_host = False
        self._player_id = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        self.stack = QtWidgets.QStackedWidget()
        self.start_page = StartPage()
        self.main_page = MainPage()
        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.main_page)
        self.setCentralWidget(self.stack)
        self.stack.setCurrentWidget(self.start_page)

    def _connect_signals(self):
        self.start_page.host_requested.connect(self._start_host)
        self.start_page.client_requested.connect(self._start_client)
        self._client.message_received.connect(self._on_message)
        self._client.error.connect(self._show_error)
        self._client.disconnected.connect(self._on_disconnected)
        self.main_page.select_script.connect(
            lambda script_id: self._client.send({"type": "select_script", "script_id": script_id})
        )
        self.main_page.set_player_count.connect(
            lambda count: self._client.send({"type": "set_player_count", "player_count": count})
        )
        self.main_page.assign_roles.connect(
            lambda: self._client.send({"type": "assign_roles"})
        )
        self.main_page.rename_requested.connect(
            lambda name: self._client.send({"type": "set_name", "display_name": name})
        )
        self.main_page.advance_phase.connect(
            lambda: self._client.send({"type": "advance_phase"})
        )
        self.main_page.reset_game.connect(
            lambda: self._client.send({"type": "reset_game"})
        )
        self.main_page.request_clue.connect(
            lambda clue_id: self._client.send({"type": "request_clue", "clue_id": clue_id})
        )
        self.main_page.submit_vote.connect(
            lambda target_id: self._client.send({"type": "submit_vote", "target_id": target_id})
        )

    def _start_host(self, name, port):
        if self._server:
            return
        try:
            self._server = GameServer(DEFAULT_HOST, port, get_scripts_path())
            self._server.start()
        except OSError as exc:
            self._server = None
            self._show_error(str(exc))
            return
        self._is_host = True
        if self._client.connect_to_host("127.0.0.1", port, name, is_host=True):
            self._enter_main()

    def _start_client(self, host, port, name):
        self._is_host = False
        if self._client.connect_to_host(host, port, name, is_host=False):
            self._enter_main()

    def _enter_main(self):
        self.main_page.set_host_mode(self._is_host)
        self.stack.setCurrentWidget(self.main_page)

    def _on_message(self, message):
        message_type = message.get("type")
        if message_type == "welcome":
            self._player_id = message.get("player_id")
            self.main_page.set_player_id(self._player_id)
            return
        if message_type == "scripts":
            self.main_page.update_scripts(message.get("scripts", []))
            return
        if message_type == "state":
            self.main_page.update_state(message.get("state", {}))
            return
        if message_type == "role_assigned":
            self.main_page.show_role(message.get("role", {}))
            return
        if message_type == "error":
            self._show_error(message.get("message", "Unknown error"))
            return

    def _on_disconnected(self):
        self._show_error("Disconnected from server. Check the host address and reconnect.")
        self.stack.setCurrentWidget(self.start_page)

    def _show_error(self, message):
        QtWidgets.QMessageBox.warning(self, "Notice", message)

    def closeEvent(self, event):
        self._client.close()
        if self._server:
            self._server.stop()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
