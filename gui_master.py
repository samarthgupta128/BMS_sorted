from tkinter import *
from tkinter import messagebox
from Serial_Com_ctrl import SerialCtrl


class RootGUI():
    def __init__(self):
        '''Initializing the root GUI and other comps of the program'''
        self.root = Tk()
        self.root.title("Serial communication")
        self.root.geometry("600x400")
        self.root.config(bg="white")


# Class to setup and create the communication manager with MCU
class ComGui():
    def __init__(self, root, serialCtrl: SerialCtrl):
        '''
        Initialize the connexion GUI and initialize the main widgets 
        '''
        # Initializing the Widgets
        self.root = root
        # serial controller instance (provided by master)
        self.serial = serialCtrl
        self.frame = LabelFrame(root, text="Com Manager",
                                padx=5, pady=5, bg="white")
        self.label_com = Label(
            self.frame, text="Available Port(s): ", bg="white", width=15, anchor="w")
        self.label_bd = Label(
            self.frame, text="Baude Rate: ", bg="white", width=15, anchor="w")

        # Setup the Drop option menu
        self.baudOptionMenu()
        self.ComOptionMenu()

        # Add the control buttons for refreshing the COMs & Connect
        self.btn_refresh = Button(self.frame, text="Refresh",
                                  width=10,  command=self.com_refresh)
        self.btn_connect = Button(self.frame, text="Connect",
                                  width=10, state="disabled",  command=self.serial_connect)

        # Add a text area to view incoming data
        self.text_frame = LabelFrame(root, text="Terminal Output", padx=5, pady=5, bg="white")
        self.text_area = Text(self.text_frame, height=12, width=60, bg="black", fg="lime")
        self.text_area.pack()

        # Optional Graphic parameters
        self.padx = 20
        self.pady = 5

        # Put on the grid all the elements
        self.publish()

        # Start reading incoming UART data
        self.read_serial_data()

    def publish(self):
        '''
         Method to display all the Widget of the main frame
        '''
        self.frame.grid(row=0, column=0, rowspan=3,
                        columnspan=3, padx=5, pady=5)
        self.label_com.grid(column=1, row=2)
        self.label_bd.grid(column=1, row=3)

        self.drop_baud.grid(column=2, row=3, padx=self.padx, pady=self.pady)
        self.drop_com.grid(column=2, row=2, padx=self.padx)

        self.btn_refresh.grid(column=3, row=2)
        self.btn_connect.grid(column=3, row=3)

        # Grid the text frame below the com manager
        self.text_frame.grid(row=4, column=0, columnspan=4, padx=5, pady=5)

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
        self.drop_com = OptionMenu(self.frame, self.clicked_com, *coms, command=self.connect_ctrl)
        self.drop_com.config(width=10)

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
            self.frame, self.clicked_bd, *bds, command=self.connect_ctrl)
        self.drop_baud.config(width=10)

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
                        self.text_area.insert(END, data_str)
                        self.text_area.see(END) # Auto-scroll to bottom
            except Exception as e:
                # This can happen if the port is closed unexpectedly
                print(f"Error reading serial data: {e}")
                self.serial.status = False # Update status

        # Repoll every 100ms without blocking the GUI
        self.root.after(100, self.read_serial_data)


if __name__ == "__main__":
    root_gui = RootGUI()
    serial_ctrl = SerialCtrl()
    com = ComGui(root_gui.root, serial_ctrl)
    root_gui.root.mainloop()
