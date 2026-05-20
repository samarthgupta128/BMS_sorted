import flet as ft
import flet_charts as charts
import asyncio
import asyncio
import random
import time

# --- THEME & COLOR PALETTE ---
BG_COLOR = "#0A0C10"  # Deep void background
SURFACE_COLOR = "#12151C"  # Raised card background
BORDER_COLOR = "#222732"  # Subtle borders
TEXT_PRIMARY = "#FFFFFF"
TEXT_MUTED = "#8B949E"
ACCENT_COLOR = "#00D084"  # Mint/Neon green for normal
WARN_COLOR = "#FFB020"  # Amber
DANGER_COLOR = "#FF4B4B"  # Coral Red


# --- CUSTOM COMPONENTS ---

class StatCard(ft.Container):
    """A minimal, tightly packed rounded card for telemetry data."""

    def __init__(self, title, initial_val="--"):
        super().__init__()
        self.bgcolor = SURFACE_COLOR
        self.border_radius = 16
        self.padding = 15
        self.border = ft.Border.all(1, BORDER_COLOR)

        self.title_text = ft.Text(title, color=TEXT_MUTED, size=11, weight=ft.FontWeight.BOLD)
        self.val_text = ft.Text(initial_val, color=TEXT_PRIMARY, size=18, weight=ft.FontWeight.BOLD)
        self.sub_text = ft.Text("", color=TEXT_MUTED, size=10, visible=False)

        self.content = ft.Column(
            controls=[
                self.title_text,
                self.val_text,
                self.sub_text
            ],
            spacing=2,
            alignment=ft.MainAxisAlignment.CENTER
        )

    def update_val(self, val_str, color=TEXT_PRIMARY, sub_str=None):
        self.val_text.value = val_str
        self.val_text.color = color
        if sub_str:
            self.sub_text.value = sub_str
            self.sub_text.visible = True
        else:
            self.sub_text.visible = False
        self.update()


class BatteryGraphic(ft.Container):
    """Animated physical representation of the battery cell."""

    def __init__(self):
        super().__init__()
        self.width = 120
        self.height = 240
        self.border = ft.Border.all(2, BORDER_COLOR)
        self.border_radius = 16
        self.bgcolor = BG_COLOR
        self.padding = 4

        # The liquid fill that animates its size and color
        self.fill = ft.Container(
            width=110,
            height=230,
            bgcolor=ACCENT_COLOR,
            border_radius=10,
            animate_size=ft.Animation(600, ft.AnimationCurve.EASE_OUT_EXPO),
            animate=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT)  # Color animation
        )

        self.content = ft.Column(
            controls=[self.fill],
            alignment=ft.MainAxisAlignment.END,  # Grow from bottom
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

    def set_level(self, capacity, state):
        height_val = (capacity / 100.0) * 230
        self.fill.height = max(10, height_val)  # Minimum height so it's visible

        if state == "Over Voltage":
            self.fill.bgcolor = DANGER_COLOR
        elif state == "Under Voltage":
            self.fill.bgcolor = WARN_COLOR
        else:
            self.fill.bgcolor = ACCENT_COLOR
        self.fill.update()


class CellBlock(ft.Container):
    """Interactive Cell Matrix Node with hover and smooth color transitions."""

    def __init__(self, segment, cell_num, on_click_callback):
        super().__init__()
        self.address = f"S{segment}C{cell_num}"
        self.on_click_callback = on_click_callback

        self.width = 45
        self.height = 35
        self.border_radius = 8
        self.bgcolor = ACCENT_COLOR
        self.animate = ft.Animation(300, ft.AnimationCurve.EASE_OUT)
        self.on_hover = self.hover_event
        self.on_click = self.click_event

        # Hardware Sim Data
        self.v = random.uniform(3.2, 4.3)
        self.t = random.uniform(25.0, 45.0)
        self.cap = random.uniform(80.0, 100.0)

        if self.v > 4.2:
            self.state = "Over Voltage"; self.bgcolor = DANGER_COLOR
        elif random.random() > 0.95:
            self.state = "Under Voltage"; self.bgcolor = WARN_COLOR
        else:
            self.state = "Normal"; self.bgcolor = ACCENT_COLOR

        self.content = ft.Text(self.address, color=BG_COLOR, size=8, weight=ft.FontWeight.BOLD,
                               text_align=ft.TextAlign.CENTER)

        # FIX: Replaced ft.alignment.center with ft.Alignment.CENTER
        self.alignment = ft.Alignment.CENTER

        self.tooltip = f"{self.address} | {self.v:.2f}V | {self.t:.1f}°C"

    def hover_event(self, e):
        e.control.scale = 1.1 if e.data == "true" else 1.0
        e.control.update()

    def click_event(self, e):
        self.on_click_callback(self.address, self.v, self.t, self.cap, self.state)


def main(page: ft.Page):
    # --- PAGE CONFIG ---
    page.title = "IIT Roorkee Motorsports | BMS"
    page.padding = 30
    page.bgcolor = BG_COLOR
    page.theme_mode = ft.ThemeMode.DARK
    page.fonts = {
        "JetBrains Mono": "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/fonts/ttf/JetBrainsMono-Regular.ttf"}
    page.theme = ft.Theme(font_family="JetBrains Mono")

    # --- SIMULATED DATA STATE ---
    telemetry = {
        "pack_v": 350.0, "max_t": 38.5, "max_cv": 4.12, "balancing": "Active",
        "status": "Normal", "ow": "No", "ov_t": 0.0, "uv_t": 0.0, "ow_v": 0.0,
        "soh": 98.4, "cycles": 142, "soc": 82.5, "cap": 94.2, "peak_i": 120.4
    }

    # --- TOP NAVIGATION BAR ---
    logo_space = ft.Container(
        width=120, height=81,
        bgcolor=SURFACE_COLOR, border_radius=12, border=ft.Border.all(1, BORDER_COLOR),
        content=ft.Text("LOGO\n120x81", color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),

        # FIX: Replaced ft.alignment.center with ft.Alignment.CENTER
        alignment=ft.Alignment.CENTER
    )

    title_text = ft.Text("IIT Roorkee Motorsports", size=22, weight=ft.FontWeight.W_700, color=TEXT_PRIMARY)

    def create_tab(name, index, visible=True):
        text = ft.Text(name, color=TEXT_MUTED, size=14, weight=ft.FontWeight.BOLD)
        underline = ft.Container(height=3, width=0, bgcolor=ACCENT_COLOR,
                                 animate_size=ft.Animation(250, ft.AnimationCurve.EASE_OUT))

        def on_hover(e):
            text.color = TEXT_PRIMARY if e.data == "true" else (ACCENT_COLOR if active_tab == index else TEXT_MUTED)
            text.update()

        def on_click(e):
            switch_tab(index)

        col = ft.Column([text, underline], spacing=4, alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        container = ft.Container(content=col, on_hover=on_hover, on_click=on_click,
                                 padding=ft.Padding(left=15, top=0, right=15, bottom=0), visible=visible)
        return container, text, underline

    active_tab = 0
    tab_home, th_txt, th_line = create_tab("Home", 0)
    tab_matrix, tm_txt, tm_line = create_tab("Cell Layout", 1)
    tab_detail, td_txt, td_line = create_tab("Cell Deep Dive", 2, visible=False)

    tabs_row = ft.Row([tab_home, tab_matrix, tab_detail], spacing=10)

    header = ft.Row([
        ft.Row([logo_space, ft.Container(width=10), title_text]),
        tabs_row
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # --- HOME TAB (DASHBOARD) ---
    cards = {
        "status": StatCard("SYSTEM PROFILE"), "bal": StatCard("BALANCING"),
        "ow": StatCard("OPEN WIRE STATE"), "soh": StatCard("STATE OF HEALTH"),
        "cyc": StatCard("CYCLE COUNT"), "soc": StatCard("STATE OF CHARGE"),
        "cap": StatCard("PACK CAPACITY"), "peak": StatCard("PEAK CURRENT")
    }

    left_metrics = ft.Container(
        content=ft.GridView(
            controls=list(cards.values()),
            runs_count=2, max_extent=200, spacing=15, run_spacing=15,
        ),
        expand=2
    )

    chart_data = [charts.LineChartDataPoint(x, 0) for x in range(50)]
    main_chart = charts.LineChart(
        data_series=[charts.LineChartData(data_points=chart_data, color=ACCENT_COLOR, stroke_width=3)],
        border=ft.Border.all(0, "transparent"),
        horizontal_grid_lines=charts.ChartGridLines(interval=1, color=BORDER_COLOR, width=1),
        vertical_grid_lines=charts.ChartGridLines(show=False),
        left_axis=charts.ChartAxis(labels_size=40, title=ft.Text("")),
        bottom_axis=charts.ChartAxis(show=False),
        tooltip_bgcolor=SURFACE_COLOR, expand=True
    )

    graph_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option("Total Pack Voltage"), ft.dropdown.Option("Maximum Temperature"),
                 ft.dropdown.Option("Maximum Cell Voltage")],
        value="Total Pack Voltage",
        width=250, border_color=BORDER_COLOR, bgcolor=BG_COLOR, text_size=12, border_radius=12, color=TEXT_PRIMARY
    )

    right_graph = ft.Container(
        bgcolor=SURFACE_COLOR, border_radius=16, border=ft.Border.all(1, BORDER_COLOR), padding=20,
        content=ft.Column([
            ft.Row([ft.Text("LIVE TELEMETRY", color=TEXT_MUTED, weight=ft.FontWeight.BOLD), graph_dropdown],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=20),
            main_chart
        ]),
        expand=3
    )

    view_home = ft.Row([left_metrics, right_graph], spacing=30, expand=True)

    # --- CELL LAYOUT TAB ---
    def cell_clicked(addr, v, t, cap, state):
        tab_detail.visible = True
        tab_detail.update()
        switch_tab(2)

        detail_title.value = f"Cell Diagnostics: {addr}"
        detail_v.value = f"{v:.3f} V"
        detail_t.value = f"{t:.1f} °C"
        detail_c.value = f"{cap:.1f}%"
        detail_s.value = state
        detail_s.color = ACCENT_COLOR if state == "Normal" else (
            DANGER_COLOR if state == "Over Voltage" else WARN_COLOR)

        detail_battery.set_level(cap, state)
        page.update()

        time.sleep(0.1)
        detail_scroll.scroll_to(offset=500, duration=800, curve=ft.AnimationCurve.EASE_IN_OUT_CUBIC)

    matrix_grid = ft.Column(spacing=10)
    for seg in range(1, 10):
        row = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        for cell in range(1, 15):
            row.controls.append(CellBlock(seg, cell, cell_clicked))
        matrix_grid.controls.append(row)

    view_matrix = ft.Container(
        content=matrix_grid, bgcolor=SURFACE_COLOR, border_radius=16, border=ft.Border.all(1, BORDER_COLOR),
        padding=30, visible=False, expand=True,

        # FIX: Replaced ft.alignment.center with ft.Alignment.CENTER
        alignment=ft.Alignment.CENTER
    )

    # --- DEEP DIVE TAB ---
    detail_battery = BatteryGraphic()
    detail_title = ft.Text("Cell Diagnostics", size=24, color=TEXT_PRIMARY, weight=ft.FontWeight.BOLD)

    def data_row(lbl, ref):
        return ft.Row([ft.Text(lbl, color=TEXT_MUTED), ref], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    detail_v = ft.Text("--", color=TEXT_PRIMARY, weight=ft.FontWeight.BOLD)
    detail_t = ft.Text("--", color=TEXT_PRIMARY, weight=ft.FontWeight.BOLD)
    detail_c = ft.Text("--", color=TEXT_PRIMARY, weight=ft.FontWeight.BOLD)
    detail_s = ft.Text("--", color=TEXT_PRIMARY, weight=ft.FontWeight.BOLD)

    detail_stats = ft.Container(
        bgcolor=SURFACE_COLOR, border_radius=16, border=ft.Border.all(1, BORDER_COLOR), padding=25, width=350,
        content=ft.Column([
            detail_title, ft.Divider(color=BORDER_COLOR),
            data_row("Voltage Rating", detail_v), data_row("Thermal Boundary", detail_t),
            data_row("Capacity Remaining", detail_c), data_row("Safety State", detail_s)
        ], spacing=15)
    )

    cell_chart_data = [charts.LineChartDataPoint(x, 0) for x in range(50)]
    cell_chart = charts.LineChart(
        data_series=[charts.LineChartData(data_points=cell_chart_data, color=WARN_COLOR, stroke_width=2)],
        border=ft.Border.all(0, "transparent"),
        horizontal_grid_lines=charts.ChartGridLines(interval=1, color=BORDER_COLOR, width=1),
        left_axis=charts.ChartAxis(labels_size=40), bottom_axis=charts.ChartAxis(show=False),
        expand=True
    )

    detail_graph_box = ft.Container(
        bgcolor=SURFACE_COLOR, border_radius=16, border=ft.Border.all(1, BORDER_COLOR), padding=20, height=350,
        content=ft.Column([
            ft.Row([
                ft.Text("CELL WAVEFORM ANALYSIS", color=TEXT_MUTED, weight=ft.FontWeight.BOLD),
                ft.Dropdown(options=[ft.dropdown.Option("Cell Voltage"), ft.dropdown.Option("Cell Temp")],
                            value="Cell Voltage", width=200, bgcolor=BG_COLOR, border_radius=8, text_size=12)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            cell_chart
        ])
    )

    detail_scroll = ft.Column(
        [
            ft.Row([detail_battery, ft.Container(width=30), detail_stats], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=40),
            detail_graph_box
        ],
        scroll=ft.ScrollMode.HIDDEN, expand=True, visible=False
    )

    # --- VIEW CONTROLLER ---
    def switch_tab(index):
        nonlocal active_tab
        active_tab = index
        th_line.width = 40 if index == 0 else 0
        tm_line.width = 40 if index == 1 else 0
        td_line.width = 40 if index == 2 else 0
        th_txt.color = ACCENT_COLOR if index == 0 else TEXT_MUTED
        tm_txt.color = ACCENT_COLOR if index == 1 else TEXT_MUTED
        td_txt.color = ACCENT_COLOR if index == 2 else TEXT_MUTED

        view_home.visible = (index == 0)
        view_matrix.visible = (index == 1)
        detail_scroll.visible = (index == 2)
        page.update()

    switch_tab(0)

    # --- FOOTER ---
    footer = ft.Row(
        [ft.Text("made with ❤️ by Samarth and Agastya [ RMS 29 ]", color="#3A404A", size=11,
                 weight=ft.FontWeight.W_500)],
        alignment=ft.MainAxisAlignment.CENTER
    )

    page.add(
        header,
        ft.Container(height=20),
        ft.Column([view_home, view_matrix, detail_scroll], expand=True),
        footer
    )

    # --- BACKGROUND DATA LOOP ---
    async def data_loop():
        x_counter = 50
        while True:
            telemetry["pack_v"] += random.uniform(-1.5, 1.5)
            telemetry["max_t"] += random.uniform(-0.2, 0.2)
            telemetry["max_cv"] = random.uniform(4.0, 4.25)

            if telemetry["max_cv"] > 4.22:
                telemetry["status"] = "Over Voltage"
                telemetry["ov_t"] = telemetry["max_t"] + 4.2
            elif telemetry["max_cv"] < 3.3:
                telemetry["status"] = "Under Voltage"
                telemetry["uv_t"] = telemetry["max_t"] - 3.1
            else:
                telemetry["status"] = "Normal"

            telemetry["ow"] = "Yes" if random.random() > 0.98 else "No"
            telemetry["ow_v"] = random.uniform(1.2, 2.4) if telemetry["ow"] == "Yes" else 0

            cards["bal"].update_val(telemetry["balancing"])

            c_color = ACCENT_COLOR if telemetry["status"] == "Normal" else DANGER_COLOR
            sub_s = None
            if telemetry["status"] == "Over Voltage":
                sub_s = f"OV Temp: {telemetry['ov_t']:.1f}°C"
            elif telemetry["status"] == "Under Voltage":
                sub_s = f"UV Temp: {telemetry['uv_t']:.1f}°C"
            cards["status"].update_val(telemetry["status"], color=c_color, sub_str=sub_s)

            ow_sub = f"Drop: {telemetry['ow_v']:.2f}V" if telemetry["ow"] == "Yes" else None
            cards["ow"].update_val(telemetry["ow"], color=DANGER_COLOR if telemetry["ow"] == "Yes" else TEXT_PRIMARY,
                                   sub_str=ow_sub)

            cards["soh"].update_val(f"{telemetry['soh']:.1f}%")
            cards["cyc"].update_val(str(telemetry["cycles"]))
            cards["soc"].update_val(f"{telemetry['soc']:.1f}%")
            cards["cap"].update_val(f"{telemetry['cap']:.1f} Ah")
            cards["peak"].update_val(f"{telemetry['peak_i']:.1f} A", color=WARN_COLOR)

            val = telemetry["pack_v"]
            if graph_dropdown.value == "Maximum Temperature":
                val = telemetry["max_t"]
            elif graph_dropdown.value == "Maximum Cell Voltage":
                val = telemetry["max_cv"]

            chart_data.pop(0)
            chart_data.append(charts.LineChartDataPoint(x_counter, val))
            main_chart.data_series[0].data_points = chart_data

            cell_chart_data.pop(0)
            cell_chart_data.append(charts.LineChartDataPoint(x_counter, random.uniform(3.5, 4.1)))
            cell_chart.data_series[0].data_points = cell_chart_data

            x_counter += 1
            page.update()
            await asyncio.sleep(0.1)

    page.run_task(data_loop)


if __name__ == "__main__":
    ft.app(target=main)