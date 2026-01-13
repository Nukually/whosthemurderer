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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scripts = {}
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
        self.players_list = QtWidgets.QListWidget()
        self.players_list.setMinimumWidth(220)
        body_layout.addWidget(self.players_list)

        role_layout = QtWidgets.QVBoxLayout()
        self.role_title = QtWidgets.QLabel("Role: -")
        self.role_intro = QtWidgets.QLabel("")
        self.role_story = QtWidgets.QTextEdit()
        self.role_story.setReadOnly(True)
        role_layout.addWidget(self.role_title)
        role_layout.addWidget(self.role_intro)
        role_layout.addWidget(self.role_story)
        body_layout.addLayout(role_layout)

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
        host_layout.addRow("Script", self.script_combo)
        host_layout.addRow(self.select_script_button)
        host_layout.addRow("Player count", self.player_count_spin)
        host_layout.addRow(self.assign_roles_button)
        layout.addWidget(self.host_controls)

    def set_host_mode(self, is_host):
        self.host_controls.setVisible(is_host)

    def update_state(self, state):
        self.phase_label.setText(f"Phase: {state.get('phase', '-')}")
        script = state.get("script")
        if script:
            self.script_label.setText(f"Script: {script.get('title', '-')}")
        else:
            self.script_label.setText("Script: -")
        self.count_label.setText(f"Players: {state.get('player_count', 0)}")
        self.players_list.clear()
        for player in state.get("players", []):
            name = player.get("display_name") or "Player"
            role_id = player.get("role_id")
            role_text = f" (Role {role_id})" if role_id else ""
            host_flag = " [Host]" if player.get("is_host") else ""
            status = "online" if player.get("connected") else "offline"
            self.players_list.addItem(f"{name}{role_text}{host_flag} - {status}")

    def update_scripts(self, scripts):
        self._scripts = {item["id"]: item for item in scripts}
        self.script_combo.clear()
        for script_id, item in self._scripts.items():
            title = item.get("title", script_id)
            self.script_combo.addItem(title, script_id)

    def show_role(self, role):
        self.role_title.setText(f"Role: {role.get('name', '-')}")
        self.role_intro.setText(role.get("intro", ""))
        self.role_story.setPlainText(role.get("story", ""))

    def _on_select_script(self):
        script_id = self.script_combo.currentData()
        if script_id:
            self.select_script.emit(script_id)

    def _on_player_count(self, value):
        self.set_player_count.emit(int(value))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Who Sthe Murder MVP")
        self.resize(900, 600)
        self._server = None
        self._client = NetworkClient()
        self._is_host = False
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
        self._show_error("Disconnected from server")
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
