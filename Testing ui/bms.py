import sys
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QGridLayout,
                             QToolTip, QScrollArea, QFrame, QPushButton, QButtonGroup)
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QFontDatabase
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtGui import QPixmap
from pathlib import Path
# Elite Dark Theme with Rounded Corners and JetBrains Mono
DARK_THEME = """
    QMainWindow {
        background-color: #0d0e12;
    }
    /* Rounded Panels */
    .Panel {
        background-color: #161920;
        border-radius: 16px;
    }
    /* Custom Tabs in Title Bar */
    QPushButton.TabBtn {
        background-color: transparent;
        color: #8a90a0;
        font-size: 15px;
        font-weight: bold;
        padding: 10px 20px;
        border: none;
        border-bottom: 3px solid transparent;
    }
    QPushButton.TabBtn:hover {
        color: #ffffff;
    }
    QPushButton.TabBtn:checked {
        color: #00ffcc;
        border-bottom: 3px solid #00ffcc;
    }
    /* Dropdown Menus */
    QComboBox {
        background-color: #232732;
        border: 1px solid #2d323f;
        border-radius: 8px;
        padding: 6px 12px;
        color: #ffffff;
        font-weight: bold;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 25px;
        border-left: 1px solid #2d323f;
    }
    QComboBox::down-arrow {
        /* Default Qt arrow will render nicely here, ensuring it looks like a dropdown */
    }
    /* Scrollbars */
    QScrollBar:vertical {
        background: #0d0e12;
        width: 10px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #2d323f;
        min-height: 20px;
        border-radius: 5px;
    }
    QToolTip {
        background-color: #161920;
        color: #ffffff;
        border: 1px solid #00ffcc;
        border-radius: 8px;
        padding: 10px;
    }
"""


class LiveGraph(FigureCanvas):
    """Real-time updating Matplotlib canvas styled for Dark Mode."""

    def __init__(self, width=5, height=4, dpi=100):
        # Match the background of the Panel (#161920)
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#161920')
        self.ax = fig.add_subplot(111, facecolor='#161920')
        self.ax.tick_params(colors='#8a90a0', labelsize=10)
        for spine in self.ax.spines.values():
            spine.set_color('#2d323f')
            spine.set_linewidth(1.5)
        self.ax.grid(True, color='#2d323f', linestyle='--', alpha=0.5)
        super().__init__(fig)
        self.x_data = list(range(50))
        self.y_data = [0.0] * 50
        self.line, = self.ax.plot(self.x_data, self.y_data, color='#00ffcc', linewidth=2.5)

        # Make the layout tight so it fits well inside the rounded box
        fig.tight_layout(pad=1.5)

    def update_plot(self, new_value, label="Value"):
        self.y_data.pop(0)
        self.y_data.append(new_value)
        self.line.set_ydata(self.y_data)
        self.line.set_label(label)
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.legend(loc='upper left', facecolor='#232732', edgecolor='#2d323f', labelcolor='white')
        self.draw()


class AnimatedBatteryCell(QWidget):
    """Custom Battery Widget displaying physical volume fill for Capacity."""

    def __init__(self, capacity_pct, state="Normal"):
        super().__init__()
        self.capacity_pct = capacity_pct
        self.state = state
        self.setMinimumSize(160, 260)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer battery shell
        painter.setPen(QColor("#2d323f"))
        painter.setBrush(QColor("#0d0e12"))
        painter.drawRoundedRect(20, 30, 120, 210, 16, 16)
        painter.drawRoundedRect(60, 15, 40, 15, 4, 4)  # Terminal

        # Fill level
        fill_height = int((self.capacity_pct / 100.0) * 190)
        fill_y = 240 - fill_height

        gradient = QLinearGradient(0, fill_y, 0, 240)
        if self.state == "Normal":
            gradient.setColorAt(0, QColor("#00ffcc"))
            gradient.setColorAt(1, QColor("#00aa88"))
        elif self.state == "Over Voltage":
            gradient.setColorAt(0, QColor("#ff4a4a"))
            gradient.setColorAt(1, QColor("#aa2222"))
        else:
            gradient.setColorAt(0, QColor("#ff9f43"))
            gradient.setColorAt(1, QColor("#cc6600"))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(30, fill_y, 100, fill_height, 10, 10)


class CellButton(QFrame):
    """Interactive Cell block for the 9x14 layout grid."""

    def __init__(self, segment, cell_idx, click_callback):
        super().__init__()
        self.segment = segment
        self.cell_idx = cell_idx
        self.callback = click_callback
        self.address = f"S{segment}C{cell_idx}"

        self.voltage = random.uniform(3.2, 4.3)
        self.temp = random.uniform(25.0, 45.0)
        self.capacity = random.uniform(80.0, 100.0)

        if self.voltage > 4.2:
            self.state = "Over Voltage"
            self.bg_color = "#ff4a4a"
        elif random.random() > 0.95:
            self.state = "Over Current"
            self.bg_color = "#ff9f43"
        else:
            self.state = "Normal"
            self.bg_color = "#2ecc71"

        self.setFixedSize(54, 44)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.bg_color};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 2px solid #ffffff;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(self.address)
        lbl.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #0d0e12;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

    def enterEvent(self, event):
        tooltip_text = (f"<b>{self.address}</b><br>"
                        f"Status: {self.state}<br>"
                        f"Voltage: {self.voltage:.2f}V<br>"
                        f"Temp: {self.temp:.1f}°C")
        QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback(self.address, self.voltage, self.temp, self.capacity, self.state)
        super().mousePressEvent(event)


class BMSDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IIT Roorkee Motorsports")
        self.resize(1300, 850)
        self.setStyleSheet(DARK_THEME)

        # Set Application Font globally
        font = QFont("JetBrains Mono", 10)
        QApplication.setFont(font)

        self.telemetry_data = {
            "pack_voltage": 350.0, "max_temp": 38.5, "max_cell_v": 4.12,
            "balancing": "Active", "status": "Normal", "open_wire": "No",
            "ov_temp": 0.0, "uv_temp": 0.0, "open_wire_v": 0.0,
            "soh": 98.4, "cycle_count": 142, "soc": 82.5, "capacity": 94.2, "peak_current": 120.4
        }

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.stream_hardware_data)
        self.timer.start(100)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 10)
        main_layout.setSpacing(15)

        # 1. Custom Title Bar Layout
        title_layout = QHBoxLayout()

        # Logo Space (120x81)
        # Logo Space (120x81)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(120, 81)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet(
            "background-color: #161920; border-radius: 12px; border: 1px solid #2d323f;")

        logo_path = Path(__file__).resolve().parent / "assets" / "iitrms_logo.jpeg"
        logo_pixmap = QPixmap(str(logo_path))
        if not logo_pixmap.isNull():
            self.logo_label.setPixmap(
                logo_pixmap.scaled(
                    self.logo_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.logo_label.setText("LOGO\n120x81")
            self.logo_label.setStyleSheet(
                "background-color: #161920; color: #8a90a0; border-radius: 12px; border: 1px dashed #2d323f;")
        title_layout.addWidget(self.logo_label)

        # Main Title (Large Font)
        title_text = QLabel("IIT Roorkee Motorsports | BMS")
        title_text.setFont(QFont("JetBrains Mono", 24, QFont.Weight.Bold))
        title_text.setStyleSheet("color: #ffffff; margin-left: 15px;")
        title_layout.addWidget(title_text)

        title_layout.addStretch()

        # Custom Tab Buttons inside Title Bar
        self.tab_group = QButtonGroup(self)

        self.btn_home = QPushButton("Home")
        self.btn_home.setProperty("class", "TabBtn")
        self.btn_home.setCheckable(True)
        self.btn_home.setChecked(True)

        self.btn_layout = QPushButton("Cell Layout")
        self.btn_layout.setProperty("class", "TabBtn")
        self.btn_layout.setCheckable(True)

        self.btn_detail = QPushButton("Cell Deep Dive")
        self.btn_detail.setProperty("class", "TabBtn")
        self.btn_detail.setCheckable(True)
        self.btn_detail.setVisible(False)  # Hidden by default

        self.tab_group.addButton(self.btn_home, 0)
        self.tab_group.addButton(self.btn_layout, 1)
        self.tab_group.addButton(self.btn_detail, 2)

        self.btn_home.clicked.connect(lambda: self.switch_tab(0))
        self.btn_layout.clicked.connect(lambda: self.switch_tab(1))
        self.btn_detail.clicked.connect(lambda: self.switch_tab(2))

        title_layout.addWidget(self.btn_home)
        title_layout.addWidget(self.btn_layout)
        title_layout.addWidget(self.btn_detail)

        main_layout.addLayout(title_layout)

        # 2. Main Stacked Layout (Replacing default tabs)
        from PyQt6.QtWidgets import QStackedWidget
        self.stack = QStackedWidget()

        self.page_home = QWidget()
        self.page_layout = QWidget()
        self.page_detail = QWidget()

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_layout)
        self.stack.addWidget(self.page_detail)
        main_layout.addWidget(self.stack)

        self.setup_home_page()
        self.setup_layout_page()
        self.setup_detail_page()

        # 3. Custom Status Bar
        status_layout = QHBoxLayout()
        status_layout.addStretch()
        status_label = QLabel("made with ❤️ by Samarth and Agastya [ RMS 29 ]")
        status_label.setFont(QFont("JetBrains Mono", 9))
        status_label.setStyleSheet("color: rgba(255, 255, 255, 0.4);")
        status_layout.addWidget(status_label)
        main_layout.addLayout(status_layout)

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)

    def setup_home_page(self):
        layout = QHBoxLayout(self.page_home)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(20)

        # Left Workspace: Unified Rounded Data Panel
        data_panel = QFrame()
        data_panel.setProperty("class", "Panel")
        data_layout = QVBoxLayout(data_panel)
        data_layout.setContentsMargins(25, 25, 25, 25)
        data_layout.setSpacing(10)  # Packed closely

        panel_title = QLabel("LIVE TELEMETRY")
        panel_title.setFont(QFont("JetBrains Mono", 16, QFont.Weight.Bold))
        panel_title.setStyleSheet("color: #00ffcc; margin-bottom: 10px;")
        data_layout.addWidget(panel_title)

        self.labels = {}
        metrics = [
            ("Balancing Status", "balancing"), ("System Profile", "status"),
            ("Open Wire State", "open_wire"), ("State of Health", "soh"),
            ("Cycle Count", "cycle_count"), ("State of Charge", "soc"),
            ("Pack Capacity", "capacity"), ("Peak Draw Current", "peak_current")
        ]

        for name, key in metrics:
            row_frame = QFrame()
            row_frame.setStyleSheet("background-color: #232732; border-radius: 8px; padding: 5px;")
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(10, 5, 10, 5)

            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("color: #8a90a0;")
            lbl_val = QLabel("0.0")
            lbl_val.setStyleSheet("color: #ffffff; font-weight: bold;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight)

            row_layout.addWidget(lbl_name)
            row_layout.addWidget(lbl_val)
            data_layout.addWidget(row_frame)
            self.labels[key] = lbl_val

        data_layout.addStretch()
        layout.addWidget(data_panel, 3)

        # Right Workspace: Rounded Graph Box with Dropdown INSIDE
        graph_box = QFrame()
        graph_box.setProperty("class", "Panel")
        graph_layout = QVBoxLayout(graph_box)
        graph_layout.setContentsMargins(20, 20, 20, 20)

        # Dropdown placed directly above the canvas, inside the rounded box
        self.graph_selector = QComboBox()
        self.graph_selector.addItems(["Total Pack Voltage", "Maximum Temperature", "Maximum Cell Voltage"])
        self.graph_selector.setMinimumHeight(40)
        graph_layout.addWidget(self.graph_selector)

        self.main_graph = LiveGraph()
        graph_layout.addWidget(self.main_graph)

        layout.addWidget(graph_box, 5)

    def setup_layout_page(self):
        layout = QVBoxLayout(self.page_layout)
        layout.setContentsMargins(0, 10, 0, 0)

        matrix_panel = QFrame()
        matrix_panel.setProperty("class", "Panel")
        grid_layout = QGridLayout(matrix_panel)
        grid_layout.setContentsMargins(25, 25, 25, 25)
        grid_layout.setSpacing(8)

        # 9 Segments x 14 Cells
        for seg in range(1, 10):
            for cell in range(1, 15):
                btn = CellButton(seg, cell, self.drill_down_cell)
                grid_layout.addWidget(btn, cell - 1, seg - 1)

        layout.addWidget(matrix_panel)

    def setup_detail_page(self):
        layout = QVBoxLayout(self.page_detail)
        layout.setContentsMargins(0, 10, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setSpacing(20)

        # Top Plane: Graphic & Data Boxes
        self.top_plane = QHBoxLayout()
        self.battery_visual = AnimatedBatteryCell(100, "Normal")
        self.top_plane.addWidget(self.battery_visual)

        self.cell_meta_layout = QVBoxLayout()
        self.lbl_detail_title = QLabel("Cell Diagnostics")
        self.lbl_detail_title.setFont(QFont("JetBrains Mono", 20, QFont.Weight.Bold))
        self.lbl_detail_title.setStyleSheet("color: #00ffcc;")
        self.cell_meta_layout.addWidget(self.lbl_detail_title)

        # Rounded box for cell stats
        stats_box = QFrame()
        stats_box.setProperty("class", "Panel")
        stats_layout = QVBoxLayout(stats_box)
        stats_layout.setContentsMargins(20, 20, 20, 20)

        self.lbl_detail_stats = QLabel("Loading data...")
        self.lbl_detail_stats.setStyleSheet("color: #ffffff; line-height: 30px;")
        stats_layout.addWidget(self.lbl_detail_stats)
        self.cell_meta_layout.addWidget(stats_box)

        self.top_plane.addLayout(self.cell_meta_layout)
        self.scroll_layout.addLayout(self.top_plane)

        # Bottom Plane: Detail Graph Box (Rounded container with internal dropdown)
        self.bottom_plane = QFrame()
        self.bottom_plane.setProperty("class", "Panel")
        bottom_layout = QVBoxLayout(self.bottom_plane)
        bottom_layout.setContentsMargins(20, 20, 20, 20)

        self.cell_graph_selector = QComboBox()
        self.cell_graph_selector.addItems(["Cell Voltage Trace", "Cell Internal Temp", "Cell Degradation Delta"])
        self.cell_graph_selector.setMinimumHeight(40)
        bottom_layout.addWidget(self.cell_graph_selector)

        self.cell_detail_graph = LiveGraph(height=3)
        bottom_layout.addWidget(self.cell_detail_graph)

        self.scroll_layout.addWidget(self.bottom_plane)

        self.scroll_area.setWidget(scroll_content)
        layout.addWidget(self.scroll_area)

    def drill_down_cell(self, addr, voltage, temp, capacity, state):
        # Reveal the hidden tab, check it, and switch page
        self.btn_detail.setVisible(True)
        self.btn_detail.setChecked(True)
        self.switch_tab(2)

        self.lbl_detail_title.setText(f"Diagnostics: {addr}")
        self.lbl_detail_stats.setText(
            f"<b>Voltage Rating:</b> <span style='color:#00ffcc'>{voltage:.3f} V</span><br><br>"
            f"<b>Thermal Boundary:</b> <span style='color:#00ffcc'>{temp:.1f} °C</span><br><br>"
            f"<b>Capacity Remaining:</b> <span style='color:#00ffcc'>{capacity:.1f}%</span><br><br>"
            f"<b>Safety State:</b> <span style='color:#00ffcc'>{state}</span>"
        )

        self.top_plane.removeWidget(self.battery_visual)
        self.battery_visual.deleteLater()
        self.battery_visual = AnimatedBatteryCell(capacity, state)
        self.top_plane.insertWidget(0, self.battery_visual)

        QTimer.singleShot(400, self.execute_smooth_scroll_transition)

    def execute_smooth_scroll_transition(self):
        anim = QPropertyAnimation(self.scroll_area.verticalScrollBar(), b"value")
        anim.setDuration(800)
        anim.setStartValue(0)
        anim.setEndValue(self.scroll_area.verticalScrollBar().maximum())
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.anim = anim
        anim.start()

    def stream_hardware_data(self):
        # Simulation Logic
        self.telemetry_data["pack_voltage"] += random.uniform(-1.5, 1.5)
        self.telemetry_data["max_temp"] += random.uniform(-0.2, 0.2)
        self.telemetry_data["max_cell_v"] = random.uniform(4.0, 4.3)

        if self.telemetry_data["max_cell_v"] > 4.22:
            self.telemetry_data["status"] = "Over Voltage"
            self.telemetry_data["ov_temp"] = self.telemetry_data["max_temp"] + 4.2
        elif self.telemetry_data["max_cell_v"] < 3.3:
            self.telemetry_data["status"] = "Under Voltage"
            self.telemetry_data["uv_temp"] = self.telemetry_data["max_temp"] - 3.1
        else:
            self.telemetry_data["status"] = "Normal"

        self.telemetry_data["open_wire"] = "Yes" if random.random() > 0.98 else "No"
        if self.telemetry_data["open_wire"] == "Yes":
            self.telemetry_data["open_wire_v"] = random.uniform(1.2, 2.4)

        # Update GUI Text
        for key, label in self.labels.items():
            val = self.telemetry_data[key]
            if isinstance(val, float):
                label.setText(f"{val:.2f}")
            else:
                label.setText(str(val))

            if key == "status":
                if val == "Normal":
                    label.setStyleSheet("color: #2ecc71; font-weight: bold;")
                else:
                    label.setStyleSheet("color: #ff4a4a; font-weight: bold;")

        # Conditional text logic
        status_text = self.telemetry_data['status']
        if status_text == "Over Voltage":
            status_text += f" ({self.telemetry_data['ov_temp']:.1f}°C)"
        elif status_text == "Under Voltage":
            status_text += f" ({self.telemetry_data['uv_temp']:.1f}°C)"
        self.labels["status"].setText(status_text)

        open_wire_text = self.telemetry_data['open_wire']
        if open_wire_text == "Yes":
            open_wire_text += f" ({self.telemetry_data['open_wire_v']:.2f}V)"
        self.labels["open_wire"].setText(open_wire_text)

        # Update Graphs
        active_selection = self.graph_selector.currentText()
        if active_selection == "Total Pack Voltage":
            self.main_graph.update_plot(self.telemetry_data["pack_voltage"], "Pack V")
        elif active_selection == "Maximum Temperature":
            self.main_graph.update_plot(self.telemetry_data["max_temp"], "Max Temp °C")
        elif active_selection == "Maximum Cell Voltage":
            self.main_graph.update_plot(self.telemetry_data["max_cell_v"], "Max Cell V")

        self.cell_detail_graph.update_plot(random.uniform(3.5, 4.1), "Live Selected Cell Waveform")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = BMSDashboard()
    dashboard.show()
    sys.exit(app.exec())