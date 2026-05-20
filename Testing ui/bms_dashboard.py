import sys
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QGridLayout,
                             QToolTip, QScrollArea, QFrame, QPushButton, QButtonGroup,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QPixmap
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pathlib import Path

# Minimal Dark Theme with Soft Blue Accents
DARK_THEME = """
    QMainWindow {
        background-color: #0d0e12;
    }
    .Panel {
        background-color: #161920;
        border-radius: 16px;
    }
    QPushButton.TabBtn {
        background-color: transparent;
        color: #8a90a0;
        font-size: 15px;
        font-weight: bold;
        padding: 10px 20px;
        border: none;
        border-bottom: 3px solid transparent;
    }
    QPushButton.TabBtn:hover { color: #ffffff; }
    QPushButton.TabBtn:checked {
        color: #ffffff;
        border-bottom: 3px solid #5ca0e6;
    }
    QComboBox {
        background-color: #232732;
        border: 1px solid #2d323f;
        border-radius: 8px;
        padding: 6px 12px;
        color: #ffffff;
        font-weight: bold;
    }
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
        border: 1px solid #5ca0e6;
        border-radius: 8px;
        padding: 10px;
    }

    /* Sleek Table Styling */
    QTableWidget {
        background-color: #161920;
        border: 1px solid #2d323f;
        border-radius: 12px;
        color: #ffffff;
        gridline-color: #2d323f;
        font-size: 15px;
    }
    QHeaderView::section {
        background-color: #232732;
        color: #8a90a0;
        padding: 12px;
        border: none;
        border-bottom: 2px solid #2d323f;
        font-weight: bold;
        font-size: 14px;
    }
    QTableWidget::item {
        padding: 10px;
        border-bottom: 1px solid #1a1d24;
    }
"""


class LiveGraph(FigureCanvas):
    def __init__(self, width=5, height=4, dpi=100):
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
        # Updated graph line color to soft blue
        self.line, = self.ax.plot(self.x_data, self.y_data, color='#5ca0e6', linewidth=2.5)
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
    def __init__(self, capacity_pct, state="Normal"):
        super().__init__()
        self.capacity_pct = capacity_pct
        self.state = state
        self.setMinimumSize(160, 260)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QColor("#2d323f"))
        painter.setBrush(QColor("#0d0e12"))
        painter.drawRoundedRect(20, 30, 120, 210, 16, 16)
        painter.drawRoundedRect(60, 15, 40, 15, 4, 4)

        fill_height = int((self.capacity_pct / 100.0) * 190)
        fill_y = 240 - fill_height

        gradient = QLinearGradient(0, fill_y, 0, 240)
        if self.state == "Normal":
            # Updated battery normal state fill to soft blue
            gradient.setColorAt(0, QColor("#5ca0e6"))
            gradient.setColorAt(1, QColor("#3b77bc"))
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
    def __init__(self, address, click_callback):
        super().__init__()
        self.address = address
        self.callback = click_callback

        self.setFixedSize(54, 44)

        # Muted green for healthy state
        self.bg_color = "#3db278"
        self.apply_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(self.address)
        lbl.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #0d0e12;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        self.v = 0.0
        self.t = 0.0
        self.cap = 0.0
        self.state = "Normal"

    def apply_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.bg_color};
                border-radius: 12px;
            }}
            QFrame:hover {{ border: 2px solid #ffffff; }}
        """)

    def update_data(self, v, t, cap, state):
        self.v = v
        self.t = t
        self.cap = cap
        self.state = state
        new_color = "#3db278"
        if state == "Over Voltage":
            new_color = "#e05a5a"
        elif state == "Under Voltage":
            new_color = "#e09f4a"

        if new_color != self.bg_color:
            self.bg_color = new_color
            self.apply_style()

    def enterEvent(self, event):
        tooltip_text = (f"<b>{self.address}</b><br>"
                        f"Status: {self.state}<br>"
                        f"Voltage: {self.v:.2f}V<br>"
                        f"Temp: {self.t:.1f}°C")
        QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback(self.address, self.v, self.t, self.cap, self.state)
        super().mousePressEvent(event)


class BMSDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IIT Roorkee Motorsports")
        self.resize(1300, 850)
        self.setStyleSheet(DARK_THEME)

        font = QFont("JetBrains Mono", 10)
        QApplication.setFont(font)

        self.pack_voltage = 350.0

        self.cells_data = []
        for seg in range(1, 10):
            for cell in range(1, 15):
                self.cells_data.append({
                    "addr": f"S{seg}C{cell}",
                    "v": random.uniform(3.2, 4.2),
                    "t": random.uniform(25.0, 45.0),
                    "cap": random.uniform(80.0, 100.0),
                    "state": "Normal"
                })

        self.cell_widgets = {}

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

        # Title Bar
        title_layout = QHBoxLayout()
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

        title_text = QLabel("IIT Roorkee Motorsports | BMS")
        title_text.setFont(QFont("JetBrains Mono", 24, QFont.Weight.Bold))
        title_text.setStyleSheet("color: #ffffff; margin-left: 15px;")
        title_layout.addWidget(title_text)
        title_layout.addStretch()

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
        self.btn_detail.setVisible(False)

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

        # Main Stacked Layout
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

        # Status Bar
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
        layout = QVBoxLayout(self.page_home)
        layout.setContentsMargins(50, 80, 50, 20)
        layout.setSpacing(40)

        # Top Panel
        voltage_container = QVBoxLayout()
        lbl_subtitle = QLabel("TOTAL PACK VOLTAGE")
        lbl_subtitle.setFont(QFont("JetBrains Mono", 16, QFont.Weight.Bold))
        lbl_subtitle.setStyleSheet("color: #8a90a0;")
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_big_voltage = QLabel("350.0 V")
        self.lbl_big_voltage.setFont(QFont("JetBrains Mono", 80, QFont.Weight.Bold))
        self.lbl_big_voltage.setStyleSheet("color: #ffffff;")
        self.lbl_big_voltage.setAlignment(Qt.AlignmentFlag.AlignCenter)

        voltage_container.addWidget(lbl_subtitle)
        voltage_container.addWidget(self.lbl_big_voltage)
        layout.addLayout(voltage_container)

        # Centered, Fixed-Size Table
        self.table = QTableWidget(3, 3)
        self.table.setHorizontalHeaderLabels(["Top 3 Max Voltages", "Bottom 3 Min Voltages", "Top 3 Max Temperatures"])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.horizontalHeader().setMinimumHeight(45)
        self.table.setFixedSize(900, 182)

        for row in range(3):
            for col in range(3):
                item = QTableWidgetItem("--")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

        table_layout = QHBoxLayout()
        table_layout.addStretch()
        table_layout.addWidget(self.table)
        table_layout.addStretch()

        layout.addLayout(table_layout)
        layout.addStretch()

    def setup_layout_page(self):
        layout = QVBoxLayout(self.page_layout)
        layout.setContentsMargins(0, 10, 0, 0)

        matrix_panel = QFrame()
        matrix_panel.setProperty("class", "Panel")
        grid_layout = QGridLayout(matrix_panel)
        grid_layout.setContentsMargins(25, 25, 25, 25)
        grid_layout.setSpacing(8)

        idx = 0
        for seg in range(1, 10):
            for cell in range(1, 15):
                cell_data = self.cells_data[idx]
                btn = CellButton(cell_data["addr"], self.drill_down_cell)
                self.cell_widgets[cell_data["addr"]] = btn
                grid_layout.addWidget(btn, cell - 1, seg - 1)
                idx += 1

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

        self.top_plane = QHBoxLayout()
        self.battery_visual = AnimatedBatteryCell(100, "Normal")
        self.top_plane.addWidget(self.battery_visual)

        self.cell_meta_layout = QVBoxLayout()
        self.lbl_detail_title = QLabel("Cell Diagnostics")
        self.lbl_detail_title.setFont(QFont("JetBrains Mono", 20, QFont.Weight.Bold))
        # Updated to clean white
        self.lbl_detail_title.setStyleSheet("color: #ffffff;")
        self.cell_meta_layout.addWidget(self.lbl_detail_title)

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
        self.btn_detail.setVisible(True)
        self.btn_detail.setChecked(True)
        self.switch_tab(2)

        self.lbl_detail_title.setText(f"Diagnostics: {addr}")
        self.lbl_detail_stats.setText(
            f"<b>Voltage Rating:</b> <span style='color:#5ca0e6'>{voltage:.3f} V</span><br><br>"
            f"<b>Thermal Boundary:</b> <span style='color:#5ca0e6'>{temp:.1f} °C</span><br><br>"
            f"<b>Capacity Remaining:</b> <span style='color:#5ca0e6'>{capacity:.1f}%</span><br><br>"
            f"<b>Safety State:</b> <span style='color:#5ca0e6'>{state}</span>"
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
        self.pack_voltage += random.uniform(-1.5, 1.5)
        self.lbl_big_voltage.setText(f"{self.pack_voltage:.1f} V")

        for cell in self.cells_data:
            cell["v"] += random.uniform(-0.01, 0.01)
            cell["v"] = max(2.5, min(cell["v"], 4.5))
            cell["t"] += random.uniform(-0.5, 0.5)

            if cell["v"] > 4.22:
                cell["state"] = "Over Voltage"
            elif cell["v"] < 3.0:
                cell["state"] = "Under Voltage"
            else:
                cell["state"] = "Normal"

            self.cell_widgets[cell["addr"]].update_data(cell["v"], cell["t"], cell["cap"], cell["state"])

        sorted_by_v_desc = sorted(self.cells_data, key=lambda x: x["v"], reverse=True)
        sorted_by_v_asc = sorted(self.cells_data, key=lambda x: x["v"])
        sorted_by_t_desc = sorted(self.cells_data, key=lambda x: x["t"], reverse=True)

        for i in range(3):
            max_v_txt = f"{sorted_by_v_desc[i]['addr']}  |  {sorted_by_v_desc[i]['v']:.3f} V"
            self.table.item(i, 0).setText(max_v_txt)

            min_v_txt = f"{sorted_by_v_asc[i]['addr']}  |  {sorted_by_v_asc[i]['v']:.3f} V"
            self.table.item(i, 1).setText(min_v_txt)

            max_t_txt = f"{sorted_by_t_desc[i]['addr']}  |  {sorted_by_t_desc[i]['t']:.1f} °C"
            self.table.item(i, 2).setText(max_t_txt)

            # Updated table danger/warning colors to be slightly muted but clearly visible
            self.table.item(i, 0).setForeground(
                QColor("#e05a5a") if sorted_by_v_desc[i]['v'] > 4.22 else QColor("#ffffff"))
            self.table.item(i, 1).setForeground(
                QColor("#e09f4a") if sorted_by_v_asc[i]['v'] < 3.0 else QColor("#ffffff"))
            self.table.item(i, 2).setForeground(
                QColor("#e05a5a") if sorted_by_t_desc[i]['t'] > 40.0 else QColor("#ffffff"))

        self.cell_detail_graph.update_plot(random.uniform(3.5, 4.1), "Live Selected Cell Waveform")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = BMSDashboard()
    dashboard.show()
    sys.exit(app.exec())