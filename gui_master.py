from tkinter import *
from tkinter import messagebox
from Serial_Com_ctrl import SerialCtrl


class RootGUI():
    def __init__(self):
        '''Initializing the root GUI and other comps of the program'''
        self.root = Tk()
est        self.root.title("BMS Monitor")
        # start with a reasonable size that fits the dashboard
        self.root.geometry("1100x700")
        # dark theme base color
        self.bg_color = "#1e1e2f"
        self.panel_color = "#242436"
        self.fg_color = "#e6e6e6"
        self.root.config(bg=self.bg_color)


# Class to setup and create the communication manager with MCU
class ComGui():
    def __init__(self, root, serialCtrl: SerialCtrl):
        '''
        Initialize the connexion GUI and initialize the main widgets
        Builds a 14-segment x 9-cell visual dashboard and parses serial data
        '''
        # Initializing the Widgets
        self.root = root
        # serial controller instance (provided by master)
        self.serial = serialCtrl

        # Styling
        self.bg = getattr(root, 'config', None)
        self.base_bg = "#1e1e2f"
        self.panel_bg = "#232331"
        self.card_bg = "#2b2b3a"
        self.text_fg = "#e6e6e6"
        self.warn_color = "#f2c94c"
        self.ok_color = "#27ae60"
        self.err_color = "#e74c3c"
        self.info_color = "#3498db"

        # Top control panel
        self.control_frame = Frame(root, bg=self.panel_bg, padx=8, pady=8)
        self.control_frame.pack(fill='x', padx=10, pady=(10, 5))

        self.label_com = Label(self.control_frame, text="Available Port(s): ", bg=self.panel_bg, fg=self.text_fg)
        self.label_bd = Label(self.control_frame, text="Baud Rate: ", bg=self.panel_bg, fg=self.text_fg)

        # Setup the Drop option menu
        self.baudOptionMenu()
        self.ComOptionMenu()

        # Add the control buttons for refreshing the COMs & Connect
        self.btn_refresh = Button(self.control_frame, text="Refresh", width=10, command=self.com_refresh)
        self.btn_connect = Button(self.control_frame, text="Connect", width=12, state="disabled", command=self.serial_connect)

        # Layout controls
        self.label_com.grid(row=0, column=0, padx=(4, 2), pady=2)
        self.drop_com.grid(row=0, column=1, padx=(0, 10), pady=2)
        self.btn_refresh.grid(row=0, column=2, padx=(0, 10), pady=2)

        self.label_bd.grid(row=0, column=3, padx=(8, 2), pady=2)
        self.drop_baud.grid(row=0, column=4, padx=(0, 10), pady=2)
        self.btn_connect.grid(row=0, column=5, padx=(0, 10), pady=2)

        # Legend
        self.legend_frame = Frame(self.control_frame, bg=self.panel_bg)
        self.legend_frame.grid(row=0, column=6, sticky='e')
        Label(self.legend_frame, text='OK', bg=self.ok_color, width=3).pack(side='left', padx=4)
        Label(self.legend_frame, text='WARN', bg=self.warn_color, width=5).pack(side='left', padx=4)
        Label(self.legend_frame, text='ALARM', bg=self.err_color, width=5).pack(side='left', padx=4)

        # Scrollable dashboard area for segments and cells
        self.board_frame = Frame(root, bg=self.base_bg)
        self.board_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # canvas + vscrollbar
        self.canvas = Canvas(self.board_frame, bg=self.base_bg, highlightthickness=0)
        self.v_scroll = Scrollbar(self.board_frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)
        self.v_scroll.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)

        self.inner_frame = Frame(self.canvas, bg=self.base_bg)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')

        # Bind resizing
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # Build the cell widgets (14 segments x 9 cells)
        self.num_segments = 14
        self.cells_per_segment = 9
        self.total_cells = self.num_segments * self.cells_per_segment
        self.cell_labels = []  # list of Label widgets for each cell
        self.segment_avg_labels = []

        self._build_dashboard()

        # Text area for raw terminal output (collapsible)
        self.text_frame = LabelFrame(root, text="Terminal Output", padx=5, pady=5, bg=self.panel_bg, fg=self.text_fg)
        self.text_area = Text(self.text_frame, height=6, bg="#0b0b0b", fg="#7CFC00")
        self.text_area.pack(fill='both', expand=True)
        self.text_frame.pack(fill='x', padx=10, pady=(0, 10))

        # Data buffering for parsing incoming stream
        self.data_buffer = ""
        self.pending_values = []
        # thresholds (example, adjust for your chemistry)
        self.ok_min = 3.7
        self.warn_min = 3.4

        # Start reading incoming UART data
        self.read_serial_data()

    def publish(self):
        '''
         Method to display all the Widget of the main frame
        '''
        # Legacy method kept for compatibility (no-op in new layout)
        return

    def ComOptionMenu(self):
        '''
         Method to Get the available COMs connected to the PC
         and list them into the drop menu
        '''
        # Generate the list of available coms using the serial controller
        try:
            coms = self.serial.getCOMList()
            if not coms:
                coms = ["-"]
        except Exception:
            coms = ["-"]

        self.clicked_com = StringVar()
        self.clicked_com.set(coms[0])
        self.drop_com = OptionMenu(self.control_frame, self.clicked_com, *coms, command=self.connect_ctrl)
        self.drop_com.config(width=12)

    def baudOptionMenu(self):
        '''
         Method to list all the baud rates in a drop menu
        '''
        self.clicked_bd = StringVar()
        bds = ["-",
               "300",
               "600",
               "1200",
               "2400",
               "4800",
               "9600",
               "14400",
               "19200",
               "28800",
               "38400",
               "56000",
               "57600",
               "115200",
               "128000",
               "256000"]
        self.clicked_bd .set(bds[0])
        self.drop_baud = OptionMenu(
            self.control_frame, self.clicked_bd, *bds, command=self.connect_ctrl)
        self.drop_baud.config(width=12)

    def connect_ctrl(self, widget):
        '''
        Mehtod to keep the connect button disabled if all the 
        conditions are not cleared
        '''
        com = self.clicked_com.get()
        bd = self.clicked_bd.get()
        # enable connect button only when both are selected and not '-'
        if com and bd and com != '-' and bd != '-':
            self.btn_connect.config(state='normal')
        else:
            self.btn_connect.config(state='disabled')

    def com_refresh(self):
        # Refresh the list of COM ports from SerialCtrl and update the OptionMenu
        try:
            coms = self.serial.getCOMList()
        except Exception:
            coms = ["-"]

        # update the OptionMenu menu
        menu = self.drop_com['menu']
        menu.delete(0, 'end')
        for c in coms:
            menu.add_command(label=c, command=lambda value=c: (self.clicked_com.set(value), self.connect_ctrl(value)))

        # reset selection
        self.clicked_com.set(coms[0] if coms else '-')
        self.connect_ctrl(None)

    def serial_connect(self):
        # Toggle connect/disconnect
        current = self.btn_connect.cget('text')

        if current.lower() == 'connect':
            # try to open serial
            ok = self.serial.SerialOpen(self)
            if ok:
                self.btn_connect.config(text='Disconnect')
                # disable selectors while connected
                self.drop_com.config(state='disabled')
                self.drop_baud.config(state='disabled')
                messagebox.showinfo('Serial', f'Connection opened ({self.serial.ser.port}@{self.serial.ser.baudrate})')
            else:
                # show last error if available
                err = getattr(self.serial, 'last_error', None)
                if err:
                    messagebox.showerror('Serial', f'Failed to open serial:\n{err}')
                else:
                    messagebox.showerror('Serial', 'Failed to open serial. Check selections and permissions.')
        else:
            # disconnect
            ok = self.serial.SerialClose(self)
            if ok:
                self.btn_connect.config(text='Connect')
                self.drop_com.config(state='normal')
                self.drop_baud.config(state='normal')
                messagebox.showinfo('Serial', 'Connection closed')
            else:
                err = getattr(self.serial, 'last_error', None)
                if err:
                    messagebox.showwarning('Serial', f'Failed to close serial:\n{err}')
                else:
                    messagebox.showwarning('Serial', 'Failed to close serial (it may already be closed)')

    def read_serial_data(self):
        '''
        Repeatedly check for incoming data if serial port is open.
        '''
        if getattr(self.serial, 'status', False) and hasattr(self.serial, 'ser') and self.serial.ser.is_open:
            try:
                # Check if data is available
                if self.serial.ser.in_waiting > 0:
                    # Read raw bytes and decode
                    raw_data = self.serial.ser.read(self.serial.ser.in_waiting)
                    data_str = raw_data.decode('utf-8', errors='replace')
                    if data_str:
                        # keep raw output for debugging
                        self.text_area.insert(END, data_str)
                        self.text_area.see(END)  # Auto-scroll to bottom
                        # parse and update dashboard
                        self._parse_incoming(data_str)
            except Exception as e:
                # This can happen if the port is closed unexpectedly
                print(f"Error reading serial data: {e}")
                self.serial.status = False # Update status

        # Repoll every 100ms without blocking the GUI
        self.root.after(100, self.read_serial_data)

    # --- Dashboard building and parsing helpers ---
    def _on_canvas_configure(self, event):
        # keep inner frame width in sync with canvas
        canvas_w = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_w)

    def _build_dashboard(self):
        # Arrange segments in 2 rows x 7 columns for visual layout
        cols = 7
        rows = (self.num_segments + cols - 1) // cols
        seg = 0
        for r in range(rows):
            for c in range(cols):
                if seg >= self.num_segments:
                    break
                card = Frame(self.inner_frame, bg=self.card_bg, bd=1, relief='raised', padx=6, pady=6)
                card.grid(row=r, column=c, padx=8, pady=8, sticky='n')
                Label(card, text=f"Segment {seg+1}", bg=self.card_bg, fg=self.text_fg, font=(None, 10, 'bold')).pack()

                # cell grid 3x3
                cell_frame = Frame(card, bg=self.card_bg)
                cell_frame.pack(pady=(6, 4))
                local_cell_labels = []
                for i in range(self.cells_per_segment):
                    # arrange 3 columns
                    rr = i // 3
                    cc = i % 3
                    lbl = Label(cell_frame, text='--', width=8, height=2, bg=self.card_bg, fg=self.text_fg, bd=1, relief='sunken')
                    lbl.grid(row=rr, column=cc, padx=4, pady=4)
                    local_cell_labels.append(lbl)
                    self.cell_labels.append(lbl)

                avg_lbl = Label(card, text='Avg: --', bg=self.card_bg, fg=self.info_color)
                avg_lbl.pack(pady=(2, 0))
                self.segment_avg_labels.append(avg_lbl)

                seg += 1

    def _parse_incoming(self, data_str: str):
        """
        Accumulate incoming text, split on commas/newlines and parse numeric values.
        When total collected values >= total_cells, update dashboard with the first frame.
        """
        # append to buffer
        self.data_buffer += data_str
        # split by commas and newlines
        tokens = []
        for part in self.data_buffer.replace('\r', '\n').split('\n'):
            if ',' in part:
                subt = [p.strip() for p in part.split(',') if p.strip() != '']
                tokens.extend(subt)
            elif part.strip() != '':
                tokens.append(part.strip())

        # try parse tokens as floats, leave remainder in buffer
        parsed = []
        remainder = ''
        for t in tokens:
            try:
                val = float(t)
                parsed.append(val)
            except Exception:
                # if cannot parse, keep for next buffer (could be partial)
                remainder += (t + '\n')

        # reset buffer to remainder
        self.data_buffer = remainder

        # append parsed to pending
        self.pending_values.extend(parsed)

        # if we have enough values to update a full frame, consume and update
        while len(self.pending_values) >= self.total_cells:
            frame_vals = self.pending_values[:self.total_cells]
            self.pending_values = self.pending_values[self.total_cells:]
            self._update_dashboard(frame_vals)

    def _update_dashboard(self, values):
        # values is list of length total_cells in order segment1 cell1..cell9, segment2...
        for idx, val in enumerate(values):
            lbl = self.cell_labels[idx]
            lbl.config(text=f"{val:.3f}")
            # choose color
            if val >= self.ok_min:
                bg = self.ok_color
            elif val >= self.warn_min:
                bg = self.warn_color
            else:
                bg = self.err_color
            lbl.config(bg=bg, fg='black')

        # update segment averages
        for s in range(self.num_segments):
            seg_vals = values[s*self.cells_per_segment:(s+1)*self.cells_per_segment]
            try:
                avg = sum(seg_vals) / len(seg_vals)
                self.segment_avg_labels[s].config(text=f"Avg: {avg:.3f}")
            except Exception:
                self.segment_avg_labels[s].config(text="Avg: --")


if __name__ == "__main__":
    root_gui = RootGUI()
    serial_ctrl = SerialCtrl()
    com = ComGui(root_gui.root, serial_ctrl)
    root_gui.root.mainloop()
