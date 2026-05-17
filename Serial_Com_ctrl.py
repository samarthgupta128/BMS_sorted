import serial.tools.list_ports  # pip install pyserial
# Secure the UART serial communication with MCU


class SerialCtrl():
    def __init__(self):
        '''
        Initializing the main varialbles for the serial data
        '''
        pass

    def getCOMList(self):
        '''
        Method that get the lost of available coms in the system
        '''
        import glob
        ports = serial.tools.list_ports.comports()
        # build list of port names and put a default '-' at index 0
        self.com_list = [com.device for com in ports]
        # Include pseudo-terminals for testing
        pts_ports = glob.glob('/dev/pts/[0-9]*')
        for pts in pts_ports:
            if pts not in self.com_list:
                self.com_list.append(pts)
        self.com_list.insert(0, "-")
        return self.com_list

    def SerialOpen(self, ComGUI):
        '''
        Method to setup the serial connection and make sure to go for the next only
        if the connection is done properly
        '''

        # read selections from GUI
        try:
            PORT = ComGUI.clicked_com.get()
            BAUDs = ComGUI.clicked_bd.get()
        except Exception:
            # invalid GUI passed
            return False

        # validate selections
        if not PORT or PORT == "-" or not BAUDs or BAUDs == "-":
            # invalid selection
            self.ser = getattr(self, 'ser', None)
            if self.ser is None:
                self.ser = None
            self.status = False
            return False

        # convert baud to int
        try:
            BAUD = int(BAUDs)
        except Exception:
            BAUD = 9600

        # try to open a serial connection
        try:
            # if serial object exists and is open, keep it
            if hasattr(self, 'ser') and self.ser is not None and getattr(self.ser, 'is_open', False):
                print("Already Open")
                self.status = True
                return True

            # create and open serial
            self.ser = serial.Serial()
            self.ser.baudrate = BAUD
            self.ser.port = PORT
            self.ser.timeout = 0.1
            self.ser.open()
            self.status = True
            return True
        except Exception as e:
            # failed to open
            self.status = False
            # keep exception for debugging and surface to caller
            self.last_error = str(e)
            print(f"SerialOpen error: {e}")
            return False

    def SerialClose(self, ComGUI):
        '''
        Method used to close the UART communication
        '''
        try:
            if hasattr(self, 'ser') and self.ser is not None and getattr(self.ser, 'is_open', False):
                self.ser.close()
            self.status = False
            return True
        except Exception as e:
            self.status = False
            self.last_error = str(e)
            print(f"SerialClose error: {e}")
            return False
