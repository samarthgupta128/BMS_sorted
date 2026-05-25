from tkinter import *
from tkinter import messagebox
from Serial_Com_ctrl import (SerialCtrl, NUM_SEGMENTS, NUM_CELLS,
                              get_cell_color, get_cell_status_label)

# ── Palette ──────────────────────────────────────────────────────────────────
# Hex color codes used throughout the UI for styling
BG, BG_PANEL, BG_CARD, BG_DARK, BG_SEG = "#1a1a2e", "#16213e", "#0f3460", "#0d2137", "#0f2744"
FG, FG_DIM, ACCENT, ACCENT2            = "#e0e0e0", "#7a8fa6", "#00d4aa", "#4ecca3"
RED, ORANGE, YELLOW, GREEN             = "#e74c3c", "#e67e22", "#f1c40f", "#2ecc71"
CELL_COLORS = {"green": GREEN, "red": RED, "orange": ORANGE, "yellow": YELLOW}

# ── Fault thresholds ─────────────────────────────────────────────────────────
# Hardcoded thresholds to visually indicate cell faults in the UI
OV_V, UV_V, OT_C, UT_C = 4.2, 2.8, 60.0, 0.0
ROWS_PER_SEG, COLS_PER_SEG = 7, 2   # Layout: 7 rows by 2 columns = 14 cells


def effective_color(serial, s, c):
    """
    Determines the cell color by checking both the hardware flags 
    and hardcoded voltage/temperature thresholds.
    Returns 'red' for faults, 'orange' for warnings, 'yellow' for balancing, 'green' for ok.
    """
    # Grab the dictionary of flags for this specific Segment (s) and Cell (c)
    f = serial.bms_data[s][c]
    
    # Grab the already-calculated voltage (Volts) and temperature (Celsius)
    v, t = serial.voltage_v(s, c), serial.temp_c(s, c)
    
    # Check for hard faults or bounds violations:
    # 1. Any hardware flag from the BMS (OverVoltage, UnderVoltage, OpenWire, OverTemp, UnderTemp)
    # 2. Any software limit crossed (v >= 4.2, v <= 2.8, etc.)
    if (f["OV"] or f["UV"] or f["OW"] or f["OWT"] or f["OT"] or f["UT"]
            or v >= OV_V or v <= UV_V or t >= OT_C or t <= UT_C):
        return "red"
        
    # Check if cell is currently balancing (from hardware 'B' flag)
    return "orange" if f["B"] else "green"


# ── Root ─────────────────────────────────────────────────────────────────────
class RootGUI:
    """Initializes the main application window (Tkinter Root)."""
    def __init__(self):
        self.root = Tk()
        self.root.title("IIT Roorkee Motorsports | BMS")
        self.root.geometry("1440x860"); self.root.minsize(1200, 880)
        self.root.config(bg=BG); self.root.resizable(True, True)


# ── Connection page ───────────────────────────────────────────────────────────
class ComGui:
    """UI for selecting and connecting to a Serial/COM port."""
    def __init__(self, root, serial, on_connect_cb=None):
        self.root = root
        self.serial = serial
        self.on_connect_cb = on_connect_cb
        self._build()

    def _dd(self, w):
        """Helper to style dropdown option menus."""
        w.config(bg=BG_CARD, fg=FG, activebackground=BG_DARK, activeforeground=ACCENT,
                 relief=FLAT, font=("Segoe UI", 10), width=13, highlightthickness=0)
        w["menu"].config(bg=BG_CARD, fg=FG, activebackground=ACCENT, activeforeground=BG)

    def _safe_coms(self):
        """Safely fetches available COM ports."""
        try:    return self.serial.getCOMList() or ["-"]
        except: return ["-"]

    def _ctrl(self, _=None):
        """Enables/disables the Connect button depending on selections."""
        ok = self.clicked_com.get() not in ('','-') and self.clicked_bd.get() not in ('','-')
        self.btn_connect.config(state='normal' if ok else 'disabled')

    def _refresh(self):
        """Refreshes the available COM ports in the dropdown."""
        coms = self._safe_coms(); menu = self.drop_com['menu']
        menu.delete(0,'end') # Clear current menu
        for c in coms:
            # Add new ports and bind to update the selection
            menu.add_command(label=c, command=lambda v=c: (self.clicked_com.set(v), self._ctrl()))
        self.clicked_com.set(coms[0] if coms else '-'); self._ctrl()

    def _connect(self):
        """Toggles serial connection and switches to dashboard on success."""
        if self.btn_connect.cget('text').lower() == 'connect':
            # Attempt to open serial port
            if self.serial.SerialOpen(self):
                self.lbl_status.config(
                    text=f"Connected: {self.serial.ser.port} @ {self.serial.ser.baudrate}", fg=ACCENT)
                self.btn_connect.config(text='Disconnect')
                self.drop_com.config(state='disabled'); self.drop_baud.config(state='disabled')
                
                # Trigger callback (moves to BMS dashboard)
                if self.on_connect_cb: self.root.after(500, self.on_connect_cb)
            else:
                messagebox.showerror('Serial',
                    f"Failed to open:\n{getattr(self.serial,'last_error','Check selections.')}")
        else:
            # Attempt to close serial port
            if self.serial.SerialClose(self):
                self.btn_connect.config(text='Connect')
                self.drop_com.config(state='normal'); self.drop_baud.config(state='normal')
                self.lbl_status.config(text="Disconnected", fg=RED)
            else:
                messagebox.showwarning('Serial', getattr(self.serial,'last_error','Failed to close.'))

    def _build(self):
        """Builds the layout of the Connection Page."""
        # Top Header Area
        hdr = Frame(self.root, bg=BG_PANEL, height=56); hdr.pack(fill=X, side=TOP)
        hdr.pack_propagate(False)
        Label(hdr, text="IIT Roorkee Motorsports  |  BMS",
              font=("Segoe UI",15,"bold"), fg=ACCENT, bg=BG_PANEL, padx=20
              ).place(relx=0, rely=0.5, anchor="w")

        # Main Centered Card
        outer = Frame(self.root, bg=BG)
        outer.pack(expand=True, fill=BOTH)
        card = Frame(outer, bg=BG_PANEL, padx=50, pady=50)
        card.place(relx=0.5, rely=0.5, anchor=CENTER)
        Label(card, text="Serial Connection", font=("Segoe UI",15,"bold"),
              fg=FG, bg=BG_PANEL).grid(row=0, column=0, columnspan=3, pady=(0,24))

        def _row(r, text, var, options):
            """Helper to create labeled OptionMenus."""
            Label(card, text=text, fg=FG, bg=BG_PANEL, font=("Segoe UI",10),
                  width=16, anchor="w").grid(row=r, column=0, padx=6, pady=10)
            var.set(options[0])
            dd = OptionMenu(card, var, *options, command=self._ctrl)
            self._dd(dd); dd.grid(row=r, column=1, padx=10, pady=10)
            return dd

        # Port Selection Row
        self.clicked_com = StringVar()
        self.drop_com = _row(1, "Available Port(s):", self.clicked_com, self._safe_coms())
        
        # Refresh Button
        Button(card, text="⟳  Refresh", width=10, command=self._refresh,
               bg=BG_CARD, fg=ACCENT2, font=("Segoe UI",9), relief=FLAT, cursor="hand2",
               activebackground=BG, activeforeground=ACCENT).grid(row=1, column=2, padx=6)

        # Baud Rate Selection Row
        self.clicked_bd = StringVar()
        bauds = ["-","300","600","1200","2400","4800","9600","14400",
                 "19200","28800","38400","56000","57600","115200","128000","256000","921600"]
        self.drop_baud = _row(2, "Baud Rate:", self.clicked_bd, bauds)

        # Connect/Disconnect Button
        self.btn_connect = Button(card, text="Connect", width=22, state="disabled",
            command=self._connect, bg=ACCENT, fg=BG, font=("Segoe UI",11,"bold"),
            relief=FLAT, cursor="hand2", activebackground=ACCENT2, activeforeground=BG,
            disabledforeground="#555")
        self.btn_connect.grid(row=3, column=0, columnspan=3, pady=(26,0))

        # Status Label
        self.lbl_status = Label(card, text="", fg=FG_DIM, bg=BG_PANEL, font=("Segoe UI",9))
        self.lbl_status.grid(row=4, column=0, columnspan=3, pady=(10,0))

        # Credit Label
        Label(outer, text="Made By Agastya and Samarth", font=("Segoe UI",11,"italic"),
              fg=FG_DIM, bg=BG).place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")


# ── BMS Dashboard ─────────────────────────────────────────────────────────────
class BMSGui:
    """UI displaying live BMS status, pack statistics, and individual cell details."""
    CARD_W, CARD_H, GAP = 210, 260, 10

    def __init__(self, root, serial, on_home_cb=None):
        self.root, self.serial, self.on_home_cb = root, serial, on_home_cb
        self._tooltip, self._cells, self._alive = None, {}, True
        self._seg_headers = {}
        
        # Build layout components
        self._build_header()
        self._build_status_bar()
        self._build_body()
        
        # Initial refresh and start polling data
        self._refresh_all()
        self._poll()

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        """Top navigation/header bar."""
        hdr = Frame(self.root, bg=BG_PANEL, height=56)
        hdr.pack(fill=X, side=TOP); hdr.pack_propagate(False)
        
        # Title
        Label(hdr, text="IIT Roorkee Motorsports  |  BMS",
              font=("Segoe UI",14,"bold"), fg=FG, bg=BG_PANEL).place(x=10, rely=0.5, anchor="w")
              
        # Nav links
        nav = Frame(hdr, bg=BG_PANEL)
        nav.place(relx=1.0, x=-12, rely=0.5, anchor="e")
        Button(nav, text="⏏  Disconnect", font=("Segoe UI",9,"bold"), fg=BG, bg=RED,
               activebackground="#c0392b", activeforeground=BG, relief=FLAT, cursor="hand2",
               padx=12, pady=5, command=self._disconnect).pack(side=LEFT, padx=(0,18))
               
        # Home indicator
        f = Frame(nav, bg=BG_PANEL); f.pack(side=LEFT)
        Label(f, text="Home", font=("Segoe UI",10,"bold"), fg=ACCENT, bg=BG_PANEL,
              padx=14, pady=4).pack()
        Frame(f, bg=ACCENT, height=2).pack(fill=X, padx=8)

    def _build_status_bar(self):
        """Bottom status bar indicating live polling."""
        bar = Frame(self.root, bg=BG_PANEL)
        bar.pack(fill=X, side=BOTTOM)
        
        self._status_bar = Label(bar, text="● Live  |  Polling every 1sec",
            font=("Segoe UI",11), fg=ACCENT, bg=BG_PANEL, anchor="w", padx=12, pady=4)
        self._status_bar.pack(side=LEFT)
        
        Label(bar, text="Made By Agastya and Samarth",
              font=("Segoe UI",11,"italic"), fg=FG_DIM, bg=BG_PANEL, padx=12, pady=4).pack(side=RIGHT)

    # ── Body ─────────────────────────────────────────────────────────────────
    def _build_body(self):
        """Main dashboard body layout, splitting into Left Panel (stats) and Right Grid (segments)."""
        body = Frame(self.root, bg=BG); body.pack(fill=BOTH, expand=True)
        CW, CH, GAP = self.CARD_W, self.CARD_H, self.GAP
        RIGHT_W = 3*CW + 4*GAP # Right section width

        # Right container for segment grids
        right = Frame(body, bg=BG, width=RIGHT_W)
        right.pack(side=RIGHT, fill=Y); right.pack_propagate(False)
        Frame(body, bg=BG_CARD, width=2).pack(side=RIGHT, fill=Y) # divider

        # Left container (scrollable) for statistics
        left_outer = Frame(body, bg=BG_PANEL)
        left_outer.pack(side=LEFT, fill=BOTH, expand=True)

        # Setup scrolling for left panel
        sb = Scrollbar(left_outer, orient=VERTICAL, bg=BG_PANEL, troughcolor=BG_DARK)
        cv = Canvas(left_outer, bg=BG_PANEL, highlightthickness=0)
        cv.configure(yscrollcommand=sb.set); sb.config(command=cv.yview)
        sb.pack(side=RIGHT, fill=Y); cv.pack(side=LEFT, fill=BOTH, expand=True)
        self._left = Frame(cv, bg=BG_PANEL)
        win = cv.create_window((0,0), window=self._left, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfig(win, width=e.width))
        self._left.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))

        self._right = right
        
        # Build contents
        self._build_left_panel(); self._build_right_segments()

    # ── Left panel ───────────────────────────────────────────────────────────
    def _build_left_panel(self):
        """Builds all the stats cards: Pack voltage, current, extremes."""
        p = self._left
        def gap(h=8):  Frame(p, bg=BG_PANEL, height=h).pack(fill=X)
        def div():     Frame(p, bg=BG_CARD, height=1).pack(fill=X, padx=14, pady=6)
        def sec(t):    Label(p, text=t, font=("Segoe UI",11,"bold"), fg=FG_DIM,
                             bg=BG_PANEL, anchor="w").pack(fill=X, padx=14, pady=(10,4))
                             
        def big_box(label, attr, color):
            f = Frame(p, bg=BG_DARK); f.pack(fill=X, padx=14)
            Label(f, text=label, font=("Segoe UI",8,"bold"), fg=FG_DIM, bg=BG_DARK).pack(pady=(10,0))
            lbl = Label(f, text="—", font=("Segoe UI",36,"bold"), fg=color, bg=BG_DARK); lbl.pack()
            Label(f, text=attr, font=("Segoe UI",9), fg=FG_DIM, bg=BG_DARK).pack(pady=(0,10))
            return lbl

        gap(12)
        # Main pack stats
        self._lbl_total_v = big_box("PACK  VOLTAGE", "Volts", ACCENT)
        gap(6)
        self._lbl_current = big_box("CURRENT", "Amps", YELLOW)

        def extremes_col(parent, title, color):
            """Creates a column for Top 3 / Bottom 3 cells."""
            col = Frame(parent, bg=BG_PANEL); col.pack(side=LEFT, fill=X, expand=True, padx=3)
            Label(col, text=title, font=("Segoe UI",10,"bold"), fg=color,
                  bg=BG_PANEL, anchor="w").pack(fill=X, pady=(0,2))
            rows = []
            for _ in range(3):
                r = Frame(col, bg=BG_DARK); r.pack(fill=X, pady=3, ipady=5)
                li = Label(r, text="—", font=("Segoe UI",11,"bold"), fg=FG,  bg=BG_DARK, width=7, anchor="w"); li.pack(side=LEFT, padx=(6,2))
                lv = Label(r, text="—", font=("Segoe UI",11,"bold"), fg=color, bg=BG_DARK);                     lv.pack(side=LEFT)
                rows.append((li, lv))
            return rows

        div(); sec("⚡  VOLTAGE EXTREMES")
        cols = Frame(p, bg=BG_PANEL); cols.pack(fill=X, padx=14, pady=(0,4))
        self._hi_v = extremes_col(cols, "▲ Highest", GREEN)
        self._lo_v = extremes_col(cols, "▼ Lowest",  RED)

        div(); sec("🌡  HOTTEST CELLS")
        self._hi_t = []
        for _ in range(3):
            r = Frame(p, bg=BG_DARK); r.pack(fill=X, padx=14, pady=2, ipady=3)
            li = Label(r, text="—", font=("Segoe UI",11,"bold"), fg=FG,     bg=BG_DARK, width=8, anchor="w"); li.pack(side=LEFT, padx=(6,2))
            lt = Label(r, text="—", font=("Segoe UI",11,"bold"), fg=ORANGE, bg=BG_DARK);                       lt.pack(side=LEFT)
            self._hi_t.append((li, lt))

        div(); sec("●  CELL STATUS")
        # Legend
        for txt, col in [("Normal", GREEN), ("Balancing active", ORANGE),
                         ("Fault (OV/UV/OT/UT/OW/OWT)", RED)]:
            r = Frame(p, bg=BG_PANEL); r.pack(anchor="w", padx=14, pady=2)
            cv = Canvas(r, width=10, height=10, bg=BG_PANEL, highlightthickness=0); cv.pack(side=LEFT, padx=(0,6))
            cv.create_oval(1,1,9,9, fill=col, outline="")
            Label(r, text=txt, fg=FG_DIM, bg=BG_PANEL, font=("Segoe UI",8)).pack(side=LEFT)
        gap(16)

    # ── Right segments ────────────────────────────────────────────────────────
    def _build_right_segments(self):
        """Constructs individual segment grids on the right."""
        CW, CH, GAP = self.CARD_W, self.CARD_H, self.GAP
        for seg in range(NUM_SEGMENTS):
            # 3 columns layout for segments
            r, c = seg//3, seg%3
            self._build_segment_card(self._right, seg, GAP + c*(CW+GAP), GAP + r*(CH+GAP), CW, CH)

    def _build_segment_card(self, parent, seg, x, y, w, h):
        """Constructs a single segment box (14 cells inside)."""
        # Outer frame for the segment card
        card = Frame(parent, bg=BG_SEG, width=w, height=h,
                     highlightbackground=BG_CARD, highlightthickness=1)
        card.place(x=x, y=y, width=w, height=h); card.pack_propagate(False)

        # Segment Header (e.g. 'S1', 'S2')
        hdr = Frame(card, bg=BG_CARD, height=22); hdr.pack(fill=X, side=TOP); hdr.pack_propagate(False)
        lbl = Label(hdr, text=f"S{seg+1} Voltage = 0.000 V", font=("Segoe UI",9,"bold"), fg=ACCENT2,
              bg=BG_CARD, anchor="center")
        lbl.place(relx=0.5, rely=0.5, anchor="center")
        self._seg_headers[seg] = lbl

        # Segment Cells Grid (Creates a flexible grid layout)
        bf = Frame(card, bg=BG_SEG); bf.pack(fill=BOTH, expand=True, padx=4, pady=4)
        
        # Configure grid column and row weights so they expand evenly
        for ci in range(COLS_PER_SEG): bf.columnconfigure(ci, weight=1, uniform="cell")
        for ri in range(ROWS_PER_SEG): bf.rowconfigure(ri, weight=1, uniform="cell")

        for ri in range(ROWS_PER_SEG):
            for ci in range(COLS_PER_SEG):
                cell = ri + ci*ROWS_PER_SEG
                
                # Each cell is represented as a button
                btn = Button(bf, text=f"C{cell+1}", font=("Segoe UI",8,"bold"),
                             relief=FLAT, cursor="hand2", bg=GREEN, fg="#0a2010",
                             activebackground=GREEN, activeforeground="#0a2010", bd=0)
                btn.grid(row=ri, column=ci, padx=2, pady=2, sticky="nsew")
                
                # Bind hover events for tooltips
                btn.bind("<Enter>", lambda e, s=seg, c=cell: self._show_tip(e, s, c))
                btn.bind("<Leave>", self._hide_tip)
                self._cells[(seg, cell)] = btn

        GAP = self.GAP
        def _resize(event, _card=card, _seg=seg):
            """Resizes cards to fill available space dynamically."""
            ncw = max(120, (event.width  - 4*GAP) // 3)
            nch = max(160, (event.height - 4*GAP) // 3)
            _r, _c = _seg//3, _seg%3
            _card.place(x=GAP+_c*(ncw+GAP), y=GAP+_r*(nch+GAP), width=ncw, height=nch)
        parent.bind("<Configure>", _resize, add="+")

    # ── Refresh ───────────────────────────────────────────────────────────────
    def _refresh_grid(self):
        """Updates the background color of each cell in the UI."""
        for (s, c), btn in self._cells.items():
            col = effective_color(self.serial, s, c)
            btn.config(bg=CELL_COLORS[col], activebackground=CELL_COLORS[col],
                       fg="#ffffff" if col == "red" else "#0a2010")

    def _refresh_stats(self):
        """Updates the numeric labels in the left panel stats."""
        sc = self.serial
        
        # Segment headers
        for seg, lbl in self._seg_headers.items():
            lbl.config(text=f"S{seg+1} Voltage = {sc.segment_voltage_v(seg):.3f} V")
        
        # Overall pack info
        self._lbl_total_v.config(text=f"{sc.total_voltage_v():.2f}")
        cur = sc.current_a()
        self._lbl_current.config(text=f"{'+' if cur>=0 else ''}{cur:.1f}")
        
        # Highest voltages
        for i, (s, c, v) in enumerate(sc.top3_voltages()):
            self._hi_v[i][0].config(text=f"S{s+1}C{c+1}"); self._hi_v[i][1].config(text=f"{v:.3f}V")
            
        # Lowest voltages
        for i, (s, c, v) in enumerate(sc.bottom3_voltages()):
            self._lo_v[i][0].config(text=f"S{s+1}C{c+1}"); self._lo_v[i][1].config(text=f"{v:.3f}V")
            
        # Hottest temperatures
        for i, (s, c, t) in enumerate(sc.top3_temps()):
            self._hi_t[i][0].config(text=f"S{s+1}C{c+1}"); self._hi_t[i][1].config(text=f"{t:.2f} °C")

    def _refresh_all(self):
        """Performs a full UI refresh based on latest serial data."""
        self._refresh_grid(); self._refresh_stats()

    # ── Tooltip ───────────────────────────────────────────────────────────────
    def _show_tip(self, event, seg, cell):
        """Shows a popup tooltip containing detailed cell status/faults on hover."""
        self._hide_tip() # Clear any existing tooltip
        
        # Grab the raw boolean flags and the actual converted float values
        f = self.serial.bms_data[seg][cell]
        v, t = self.serial.voltage_v(seg, cell), self.serial.temp_c(seg, cell)
        col = effective_color(self.serial, seg, cell)
        
        # Combine hardware flags with software bounds checking to create "effective" flags
        eff = {**f, "OV": f["OV"] or v>=OV_V, "UV": f["UV"] or v<=UV_V,
                     "OT": f["OT"] or t>=OT_C, "UT": f["UT"] or t<=UT_C}
                     
        # Collect all active fault messages into a list
        errs = [lbl for k,lbl in [("OV","Over Voltage"),("UV","Under Voltage"),
                ("OT","Over Temp"),("UT","Under Temp"),("OW","Open Wire V"),("OWT","Open Wire T")]
                if eff[k]]
        # Join faults with a comma, or show "Normal" if list is empty
        status = ", ".join(errs) if errs else "Normal"

        # Create Toplevel popup window for tooltip
        tip = Toplevel(self.root); tip.wm_overrideredirect(True)
        tip.wm_attributes("-topmost", True); tip.configure(bg=BG_PANEL)
        inner = Frame(tip, bg=BG_CARD, padx=14, pady=10); inner.pack(padx=1, pady=1)

        # Header of tooltip
        hr = Frame(inner, bg=BG_CARD); hr.pack(fill=X, pady=(0,6))
        Label(hr, text=f"S{seg+1}C{cell+1}", font=("Segoe UI",13,"bold"), fg=FG,
              bg=BG_CARD).pack(side=LEFT, padx=(0,10))
        chip_col = CELL_COLORS[col]
        Label(hr, text=f"  {status}  ", font=("Segoe UI",8,"bold"),
              fg="#ffffff" if col=="red" else "#0a2010", bg=chip_col,
              padx=4, pady=2).pack(side=LEFT)
        Frame(inner, bg=BG_PANEL, height=1).pack(fill=X, pady=(0,6))

        # Values of tooltip
        mr = Frame(inner, bg=BG_CARD); mr.pack(fill=X, pady=(0,6))
        Label(mr, text=f"⚡  {v:.3f} V", font=("Segoe UI",10,"bold"),
              fg=RED if (v>=OV_V or v<=UV_V) else ACCENT, bg=BG_CARD).pack(side=LEFT, padx=(0,18))
        Label(mr, text=f"🌡  {t:.2f} °C", font=("Segoe UI",10,"bold"),
              fg=ORANGE if (t>=OT_C or t<=UT_C) else FG, bg=BG_CARD).pack(side=LEFT)
        Frame(inner, bg=BG_PANEL, height=1).pack(fill=X, pady=(0,6))

        # List all flags
        for key, desc in [("OV","Over Voltage"),("UV","Under Voltage"),("OT","Over Temp"),
                           ("UT","Under Temp"),("OW","Open Wire V"),("OWT","Open Wire T"),("B","Balancing")]:
            r = Frame(inner, bg=BG_CARD); r.pack(anchor="w", pady=1)
            val = eff[key]
            
            if key == "B":
                icon_color = GREEN if val else RED
            else:
                icon_color = RED if val else GREEN
                
            Label(r, text="✔" if val else "✖", fg=icon_color,
                  bg=BG_CARD, font=("Segoe UI",8,"bold"), width=2).pack(side=LEFT)
            Label(r, text=desc, fg=FG, bg=BG_CARD, font=("Segoe UI",8)).pack(side=LEFT)

        # Position tooltip at cursor
        tip.wm_geometry(f"+{self.root.winfo_pointerx()+16}+{self.root.winfo_pointery()+16}")
        self._tooltip = tip

    def _hide_tip(self, event=None):
        """Destroys the current tooltip popup."""
        if self._tooltip:
            try:    self._tooltip.destroy()
            except: pass
            self._tooltip = None

    # ── Poll ──────────────────────────────────────────────────────────────────
    def _poll(self):
        """Background poll loop runs every 1s to read UART data and update UI."""
        if not self._alive: return
        try:
            # Tell the serial controller to read from the port and parse any complete frames.
            # If it returns True, it means new data was parsed, so we refresh the screen.
            if self.serial.read_and_parse(): 
                self._refresh_all()
                
            # Update the tiny status bar at the bottom depending on connection state
            live = getattr(self.serial, 'status', False)
            self._status_bar.config(
                text="● Live  |  Polling every 1sec" if live else "○ Disconnected",
                fg=ACCENT if live else RED)
        except TclError:
            # Tkinter might throw TclError if the window was closed during the middle of a poll
            self._alive = False; return
            
        # Schedule this exact function to run again in 1000 milliseconds (1 second)
        self.root.after(1000, self._poll)

    def _disconnect(self):
        """Disconnects serial port and switches UI back to ComGui."""
        self._alive = False; self._hide_tip()
        try:
            if hasattr(self.serial,'ser') and self.serial.ser and self.serial.ser.is_open:
                self.serial.ser.close()
            self.serial.status = False
        except: pass
        
        # Clear UI and instantiate Connection Page
        for w in self.root.winfo_children(): w.destroy()
        ComGui(self.root, self.serial, on_connect_cb=lambda: [
            [w.destroy() for w in self.root.winfo_children()],
            BMSGui(self.root, self.serial)])

    def destroy(self):
        """Cleans up when UI is closing."""
        self._alive = False; self._hide_tip()


# ── App controller ────────────────────────────────────────────────────────────
class AppController:
    """Manages switching between different screens (Connection / Dashboard)."""
    def __init__(self, root, serial):
        self.root = root
        self.serial = serial
        self._page = None
        self._show_connection()

    def _clear(self):
        """Destroys current page contents before loading a new one."""
        if self._page and hasattr(self._page, 'destroy'): self._page.destroy()
        for w in self.root.winfo_children(): w.destroy()

    def _show_connection(self):
        """Renders the COM Port connection view."""
        self._clear()
        self._page = ComGui(self.root, self.serial, on_connect_cb=self._show_dashboard)

    def _show_dashboard(self):
        """Renders the main BMS dashboard view."""
        self._clear()
        self._page = BMSGui(self.root, self.serial)


if __name__ == "__main__":
    # Standard boilerplate for starting the app if run directly
    root = RootGUI()
    AppController(root.root, SerialCtrl())
    root.root.mainloop()
