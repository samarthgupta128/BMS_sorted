import serial.tools.list_ports, struct, glob

# ─────────────────────────────────────────────────────────────────────────
# BMS UART Frame layout (little-endian throughout):
#
#   FRAME_HEADER  : 2 bytes  = 0xAA 0x55
#   flags[]       : 126 bytes (9 seg × 14 cells, 1 byte each)
#                   each byte = [OV UV OT UT OW OWT B 0]  (bit 7 → 0)
#   voltages[]    : 252 bytes (9×14 int16, mV per cell, big-endian)
#   temps[]       : 252 bytes (9×14 int16, 0.1 °C per cell, big-endian)
#   current       : 2 bytes   int16, Amps × 10  (signed)
#   ─────────────────────────────────────────────────────────────────
#   Total         : 2 + 126 + 252 + 252 + 2 = 634 bytes
#
# If your firmware does NOT send the full extended frame yet, set
# EXTENDED_FRAME = False and the parser falls back to the old 126-byte
# flag-only mode (voltages/temps stay at their default values).
# ─────────────────────────────────────────────────────────────────────────

EXTENDED_FRAME = True
NUM_SEGMENTS, NUM_CELLS = 9, 14
FRAME_HEADER   = bytes([0xAA, 0x55]) # 0xAA55 header to indicate start of frame
FLAGS_SIZE     = NUM_SEGMENTS * NUM_CELLS          # 126 bytes for flags
VOLTAGES_SIZE  = FLAGS_SIZE * 2                    # 252 bytes (2 bytes per cell voltage)
TEMPS_SIZE     = FLAGS_SIZE * 2                    # 252 bytes (2 bytes per cell temp)
HEADER_SIZE    = 2
PACKET_SIZE_EXT   = HEADER_SIZE + FLAGS_SIZE + VOLTAGES_SIZE + TEMPS_SIZE + 2  # 634 bytes total extended
PACKET_SIZE_BASIC = FLAGS_SIZE # 126 bytes for basic frame

# Bit positions in each flag byte (e.g. OV is bit 7, UV is bit 6, etc.)
_BITS = dict(OV=7, UV=6, OT=5, UT=4, OW=3, OWT=2, B=1)
# Default values used when extended frame is missing (raw int16_t values)
DEFAULT_RAW_VOLTAGE = 14666 # ~3.7V
DEFAULT_RAW_TEMP    = 2400  # ~25.0C

# Look-up tables for temperature interpolation
TEMP_TABLE = [
    -40.0, -35.0, -30.0, -25.0, -20.0, -15.0, -10.0, -5.0, 0.0,
      5.0,  10.0,  15.0,  20.0,  25.0,  30.0,  35.0,  40.0,
     45.0,  50.0,  55.0,  60.0,  65.0,  70.0,  75.0,  80.0,
     85.0,  90.0,  95.0, 100.0, 105.0, 110.0, 115.0, 120.0
]

VOLT_TABLE = [
    2.44, 2.42, 2.40, 2.38, 2.35, 2.32, 2.27, 2.23, 2.17,
    2.11, 2.05, 1.99, 1.92, 1.86, 1.80, 1.74, 1.68,
    1.63, 1.59, 1.55, 1.51, 1.48, 1.45, 1.43, 1.40,
    1.38, 1.37, 1.35, 1.34, 1.33, 1.32, 1.31, 1.30
]

def calculate_cell_voltage(raw_input: int) -> float:
    """
    Converts raw int16_t from the BMS analog-to-digital converter to the final cell voltage.
    The hardware scales the reading such that Voltage = (Raw * 0.00015) + 1.5.
    """
    return (raw_input * 0.00015) + 1.5

def voltage_to_temperature(raw_input: int) -> float:
    """
    Converts raw int16_t to temperature using linear interpolation against a lookup table.
    The BMS reads temperature as an analog voltage from an NTC thermistor.
    """
    # First, calculate the voltage equivalent from the raw ADC value
    v = (raw_input * 0.00015) + 1.5
    
    # Boundary checks: If the voltage is outside our known lookup table bounds,
    # clamp the temperature to the maximum or minimum table values.
    if v >= VOLT_TABLE[0]:
        return TEMP_TABLE[0]
    if v <= VOLT_TABLE[-1]:
        return TEMP_TABLE[-1]
        
    table_size = len(VOLT_TABLE)
    
    # Iterate through the voltage table to find which interval the voltage falls into.
    for i in range(table_size - 1):
        v1 = VOLT_TABLE[i]
        v2 = VOLT_TABLE[i + 1]
        
        # Check if the voltage 'v' is within the current interval [v1, v2]
        # Note: the VOLT_TABLE is in descending order, so v1 > v2.
        if v <= v1 and v >= v2:
            t1 = TEMP_TABLE[i]
            t2 = TEMP_TABLE[i + 1]
            
            # Apply linear interpolation formula: 
            return t1 + (v - v1) * (t2 - t1) / (v2 - v1)
            
    # Fallback return in case the table iteration fails (should not happen due to clamps above)
    return 0.0



def _blank_flags():
    """Returns a dictionary with all fault/status flags set to False."""
    return {k: False for k in _BITS}

def parse_cell_byte(b):
    """
    Parses a single flag byte and extracts the boolean statuses based on _BITS.
    Example: 
      b = 0b10000000 (128)
      Bit 7 is 'OV'. (1 << 7) is 128.
      (128 & 128) == True, so 'OV' becomes True.
    """
    return {k: bool(b & (1 << v)) for k, v in _BITS.items()}

def get_cell_status_label(flags):
    """Returns a string describing the current faults/status of a cell."""
    msgs = [lbl for k, lbl in [("OV","Over Voltage"),("UV","Under Voltage"),
            ("OT","Over Temp"),("UT","Under Temp"),("OW","Open Wire (V)"),
            ("OWT","Open Wire (T)")] if flags[k]]
    return ", ".join(msgs) if msgs else "Normal"

def get_cell_color(flags):
    """Determines the color representing the cell's status (Red=Fault, Orange=Warning, Yellow=Balancing, Green=Normal)."""
    if any(flags[k] for k in ("OV","UV","OW","OWT","OT","UT")): return "red"
    if flags["B"]:                                      return "orange"
    return "green"


class SerialCtrl:
    """Manages the serial communication with the BMS and parses incoming data."""
    def __init__(self):
        self._rx_buffer = bytearray() # Buffer to accumulate incoming bytes
        
        # 2D arrays to hold BMS data (Segment -> Cell -> Value)
        self.bms_data = [[_blank_flags()        for _ in range(NUM_CELLS)] for _ in range(NUM_SEGMENTS)]
        self.voltages = [[DEFAULT_RAW_VOLTAGE   for _ in range(NUM_CELLS)] for _ in range(NUM_SEGMENTS)]
        self.temps    = [[DEFAULT_RAW_TEMP      for _ in range(NUM_CELLS)] for _ in range(NUM_SEGMENTS)]
        self.current  = 0
        self.bms_update_callback = None

    # ── Accessors ────────────────────────────────────────────────────────────
    def voltage_v(self, s, c):  
        """Gets cell voltage in Volts."""
        return calculate_cell_voltage(self.voltages[s][c])
        
    def temp_c(self, s, c):     
        """Gets cell temperature in Celsius."""
        return voltage_to_temperature(self.temps[s][c])
        
    def current_a(self):        
        """Gets total pack current in Amps."""
        return self.current / 10.0

    def total_voltage_v(self):
        """Calculates total pack voltage by summing all cell voltages."""
        return sum(self.voltage_v(s, c)
                   for s in range(NUM_SEGMENTS) for c in range(NUM_CELLS))

    def segment_voltage_v(self, s):
        """Calculates total voltage of a specific segment."""
        return sum(self.voltage_v(s, c) for c in range(NUM_CELLS))

    def _sorted_cells(self, key_fn, n=3):
        """Helper to sort all cells by a given function and return top 'n'. Excludes cells with Open Wire (V) faults."""
        return sorted([(s, c, self.voltage_v(s, c))
                       for s in range(NUM_SEGMENTS) for c in range(NUM_CELLS)
                       if not self.bms_data[s][c]["OW"]],
                      key=key_fn)[:n]

    def top3_voltages(self):    
        """Returns the top 3 highest cell voltages."""
        return self._sorted_cells(lambda x: -x[2])
        
    def bottom3_voltages(self): 
        """Returns the top 3 lowest cell voltages."""
        return self._sorted_cells(lambda x:  x[2])

    def top3_temps(self):
        """Returns the top 3 highest cell temperatures. Excludes cells with Open Wire (T) faults."""
        return sorted([(s, c, self.temp_c(s, c))
                       for s in range(NUM_SEGMENTS) for c in range(NUM_CELLS)
                       if not self.bms_data[s][c]["OWT"]],
                      key=lambda x: -x[2])[:3]

    # ── Port helpers ─────────────────────────────────────────────────────────
    def getCOMList(self):
        """Retrieves a list of available COM/Serial ports on the system."""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        for p in glob.glob('/dev/pts/[0-9]*'): # For Linux virtual ports
            if p not in ports: ports.append(p)
        self.com_list = ["-"] + ports
        return self.com_list

    def SerialOpen(self, ComGUI):
        """Opens the selected serial port using the given baud rate."""
        try:
            PORT, BAUDs = ComGUI.clicked_com.get(), ComGUI.clicked_bd.get()
        except Exception:
            return False
            
        if not PORT or PORT == "-" or not BAUDs or BAUDs == "-":
            self.status = False; return False
            
        try:
            if hasattr(self, 'ser') and self.ser and getattr(self.ser, 'is_open', False):
                self.status = True; return True
                
            # Open the port with a short timeout
            self.ser = serial.Serial(port=PORT, baudrate=int(BAUDs), timeout=0.1)
            if not self.ser.is_open:
                self.ser.open()
                
            self.status = True
            self._rx_buffer = bytearray() # Reset buffer on open
            return True
        except Exception as e:
            self.status = False; self.last_error = str(e); return False

    def SerialClose(self, _):
        """Closes the active serial port connection."""
        try:
            if hasattr(self, 'ser') and self.ser and getattr(self.ser, 'is_open', False):
                self.ser.close()
            self.status = False; return True
        except Exception as e:
            self.status = False; self.last_error = str(e); return False

    # ── UART parsing ─────────────────────────────────────────────────────────
    def read_and_parse(self):
        """Reads incoming bytes from the serial port and attempts to parse frames."""
        if not (getattr(self, 'status', False) and hasattr(self, 'ser') and self.ser.is_open):
            return False
        try:
            n = self.ser.in_waiting
            if n > 0:
                self._rx_buffer.extend(self.ser.read(n))
                # Choose parser based on frame type setting
                return self._parse_extended() if EXTENDED_FRAME else self._parse_basic()
        except Exception as e:
            print(f"read_and_parse error: {e}"); self.status = False
        return False

    def _parse_extended(self):
        """Parses the extended 634-byte frame, aligning to FRAME_HEADER."""
        updated = False
        while True:
            idx = self._rx_buffer.find(FRAME_HEADER)
            
            # If header is not found
            if idx == -1:
                # Keep the last byte just in case it's half of the header (e.g. 0xAA)
                if len(self._rx_buffer) > 1: self._rx_buffer = self._rx_buffer[-1:]
                break
                
            # If header found but not at start, discard garbage before it
            if idx > 0: del self._rx_buffer[:idx]
            
            # Wait until we have enough bytes for a full extended packet
            if len(self._rx_buffer) < PACKET_SIZE_EXT: break
            
            # Apply parsing to the complete frame
            self._apply_extended_frame(bytes(self._rx_buffer[:PACKET_SIZE_EXT]))
            
            # Consume the parsed frame from the buffer
            del self._rx_buffer[:PACKET_SIZE_EXT]
            updated = True
        return updated

    def _parse_basic(self):
        """Parses the basic 126-byte frame (flags only). No header alignment."""
        updated = False
        while len(self._rx_buffer) >= PACKET_SIZE_BASIC:
            self._apply_basic_frame(bytes(self._rx_buffer[:PACKET_SIZE_BASIC]))
            del self._rx_buffer[:PACKET_SIZE_BASIC]; updated = True
        return updated

    def _apply_extended_frame(self, frame):
        """
        Extracts flags, voltages, temps, and current from a full extended frame byte array.
        Uses Python's struct.unpack_from to convert chunks of bytes directly into integers.
        """
        b = HEADER_SIZE
        
        # 1. Parse status flags (1 byte per cell)
        for s in range(NUM_SEGMENTS):
            for c in range(NUM_CELLS):
                # Calculate array index for the specific segment and cell
                self.bms_data[s][c] = parse_cell_byte(frame[b + s*NUM_CELLS + c])
                
        # 2. Parse voltages (Big-Endian int16)
        # Shift the read offset 'vb' forward by the size of the flags section
        vb = b + FLAGS_SIZE
        for s in range(NUM_SEGMENTS):
            for c in range(NUM_CELLS):
                off = vb + (s*NUM_CELLS + c)*2
                # unpack_from('>h') reads 2 bytes at 'off' as a big-endian signed short
                self.voltages[s][c] = struct.unpack_from('>h', frame, off)[0]
                
        # 3. Parse temperatures (Big-Endian int16)
        # Shift the read offset 'tb' forward by the size of the voltages section
        tb = vb + VOLTAGES_SIZE
        for s in range(NUM_SEGMENTS):
            for c in range(NUM_CELLS):
                off = tb + (s*NUM_CELLS + c)*2
                # unpack_from('>h') reads 2 bytes at 'off' as a big-endian signed short
                self.temps[s][c] = struct.unpack_from('>h', frame, off)[0]
                
        # 4. Parse current (Big-Endian int16)
        # Current is the final 2 bytes after the temperature section
        self.current = struct.unpack_from('>h', frame, tb + TEMPS_SIZE)[0]

    def _apply_basic_frame(self, frame):
        """Extracts status flags from a basic frame."""
        for s in range(NUM_SEGMENTS):
            for c in range(NUM_CELLS):
                self.bms_data[s][c] = parse_cell_byte(frame[s*NUM_CELLS + c])
