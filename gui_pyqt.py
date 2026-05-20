import sys
import json
import pyqtgraph as pg
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QPushButton,
                             QStackedWidget, QScrollArea, QGridLayout, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

from Serial_Com_ctrl import SerialCtrl

class LoginScreen(QWidget):
    def __init__(self, serial_ctrl, on_connect):
        super().__init__()
        self.serial = serial_ctrl
        self.on_connect = on_connect

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("IIT RMS - Login")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title, alignment=Qt.AlignCenter)

        self.port_combo = QComboBox()
        self.port_combo.addItems(self.serial.getCOMList())
        layout.addWidget(QLabel("Select Port:", styleSheet="color: white;"))
        layout.addWidget(self.port_combo)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "115200"])
        layout.addWidget(QLabel("Baud Rate:", styleSheet="color: white;"))
        layout.addWidget(self.baud_combo)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setStyleSheet("background-color: #7289da; color: white; padding: 10px; border-radius: 5px;")
        self.btn_connect.clicked.connect(self.connect_serial)
        layout.addWidget(self.btn_connect)

        self.setLayout(layout)

    def connect_serial(self):
        # mock for now so we can test the UI without real serial
        port = self.port_combo.currentText()
        # In a real app we'd call self.serial.SerialOpen(...)
        self.on_connect(port)

class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Top Bar
        top_bar = QHBoxLayout()
        welcome = QLabel("Welcome to IIT RMS Dashboard")
        welcome.setFont(QFont("Arial", 18, QFont.Bold))
        top_bar.addWidget(welcome)
        layout.addLayout(top_bar)

        # Data Cards
        cards_layout = QHBoxLayout()
        self.pack_voltage_lbl = QLabel("Pack Voltage: -- V")
        self.pack_current_lbl = QLabel("Total Current: -- A")
        self.soc_lbl = QLabel("SOC: -- %")

        for lbl in (self.pack_voltage_lbl, self.pack_current_lbl, self.soc_lbl):
            lbl.setStyleSheet("background-color: #2c2f33; color: white; padding: 20px; border-radius: 10px; font-size: 16px;")
            cards_layout.addWidget(lbl)

        layout.addLayout(cards_layout)

        # Graph
        self.plot_widget = pg.PlotWidget(title="Live Voltage")
        self.plot_widget.setBackground('#23272a')
        self.plot_curve = self.plot_widget.plot(pen=pg.mkPen('#7289da', width=2))
        layout.addWidget(self.plot_widget)

        self.y_data = []
        self.setLayout(layout)

    def update_data(self, data):
        self.pack_voltage_lbl.setText(f"Pack Voltage:\n{data.get('pack_voltage', '--')} V")
        self.pack_current_lbl.setText(f"Total Current:\n{data.get('total_current', '--')} A")
        self.soc_lbl.setText(f"SOC:\n{data.get('soc', '--')} %")

        self.y_data.append(data.get('pack_voltage', 0))
        if len(self.y_data) > 50:
            self.y_data.pop(0)
        self.plot_curve.setData(self.y_data)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IIT RMS")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #23272a; color: white;")

        self.serial_ctrl = SerialCtrl()
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.login_screen = LoginScreen(self.serial_ctrl, self.go_to_dashboard)
        self.dashboard = Dashboard()

        self.stacked_widget.addWidget(self.login_screen)
        self.stacked_widget.addWidget(self.dashboard)

        # Serial Polling Timer (Dummy for now)
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_serial)

    def go_to_dashboard(self, port):
        self.current_port = port
        self.stacked_widget.setCurrentWidget(self.dashboard)
        # Attempt to open serial port if possible
        try:
            import serial
            self.ser = serial.Serial(port, 9600, timeout=0.1)
        except:
            self.ser = None
        self.buffer = ""
        self.timer.start(100) # Poll every 100ms

    def poll_serial(self):
        if hasattr(self, 'ser') and self.ser:
            try:
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='replace')
                    self.buffer += chunk
                    if '\n' in self.buffer:
                        lines = self.buffer.split('\n')
                        self.buffer = lines[-1]
                        for line in lines[:-1]:
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    self.dashboard.update_data(data)
                                except json.JSONDecodeError:
                                    pass
            except Exception as e:
                print(e)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

