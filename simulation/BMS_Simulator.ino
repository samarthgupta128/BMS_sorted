// ============================================================
//  BMS Fake Data Simulator
//  IIT Roorkee Motorsports
//
//  Sends a 634-byte frame every 500 ms over Serial (USB).
//
//  Frame layout (matches Serial_Com_ctrl.py EXTENDED_FRAME):
//    [0x AA, 0x55]          – 2 bytes header
//    flags[9][14]           – 126 bytes  (1 byte per cell)
//    voltages[9][14]        – 252 bytes  (int16 big-endian, RAW ADC values)
//    temps[9][14]           – 252 bytes  (int16 big-endian, RAW ADC values)
//    current                –   2 bytes  (int16 big-endian, A × 10)
//
//  Bit layout of each flag byte  (bit 7 → bit 0):
//    [OV | UV | OT | UT | OW | OWT | B | 0]
//
//  Set BAUD_RATE to match whatever you pick in the Python GUI.
// ============================================================

#define BAUD_RATE   115200

#define NUM_SEG      9
#define NUM_CELLS   14

// ── Fault injection ─────────────────────────────────────────
//  faultCell : which cell to make "bad" in the randomly chosen segment
#define FAULT_CELL   4          // 0-based  (C5 in GUI)

// ── Timing ──────────────────────────────────────────────────
#define FRAME_INTERVAL_MS  250  // send a frame every 250 ms

// ── Voltage simulation ──────────────────────────────────────
// Python calculates: V = raw * 0.00015 + 1.5 
#define V_NOM_RAW    14666      // ~ 3.700 V
#define V_SPREAD_RAW 1333       // ~ ± 0.100 V spread (1333 raw units)

// ── Temperature simulation ──────────────────────────────────
// Python interpolates temperature from the calculated V.
// For 25.0 °C, V = 1.86. So raw = (1.86 - 1.5) / 0.00015 = 2400
#define T_NOM_RAW     2400      // ~ 25.0 °C
#define T_SPREAD_RAW  400       // spread for temp drift

// ── Current simulation ──────────────────────────────────────
#define I_AMP10_MAX   500
#define I_AMP10_MIN  -200

// ────────────────────────────────────────────────────────────
//  Helpers
// ────────────────────────────────────────────────────────────

// Simple LCG pseudo-random (avoids Arduino random() seed issues)
static uint32_t _rng = 12345UL;
uint32_t lcg() {
    _rng = _rng * 1664525UL + 1013904223UL;
    return _rng;
}
// Returns value in [lo, hi]
int32_t randRange(int32_t lo, int32_t hi) {
    return lo + (int32_t)(lcg() % (uint32_t)(hi - lo + 1));
}

// Write uint16 big-endian
void writeU16BE(uint16_t v) {
    Serial.write((uint8_t)(v >> 8));
    Serial.write((uint8_t)(v & 0xFF));
}
// Write int16 big-endian
void writeI16BE(int16_t v) {
    writeU16BE((uint16_t)v);
}

// ────────────────────────────────────────────────────────────
//  State that evolves each frame
// ────────────────────────────────────────────────────────────
int16_t  voltages[NUM_SEG][NUM_CELLS];   // RAW ADC
int16_t  temps   [NUM_SEG][NUM_CELLS];   // RAW ADC
int16_t  current_a10 = 0;               // A × 10

// Drift direction per cell (+1 or -1 in raw ADC steps)
int8_t   vDir   [NUM_SEG][NUM_CELLS];
int8_t   tDir   [NUM_SEG][NUM_CELLS];
int8_t   iDir = 1;

uint8_t  frameCounter = 0;  // cycles fault type every N frames

// ────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(BAUD_RATE);
    delay(200);

    // Seed the RNG with an analog noise read
    _rng ^= (uint32_t)analogRead(A0) * 6364136223846793005ULL;

    // Initialise voltages and temperatures with small random offsets
    for (int s = 0; s < NUM_SEG; s++) {
        for (int c = 0; c < NUM_CELLS; c++) {
            voltages[s][c] = V_NOM_RAW + randRange(-V_SPREAD_RAW/2, V_SPREAD_RAW/2);
            temps   [s][c] = T_NOM_RAW + randRange(-T_SPREAD_RAW/2, T_SPREAD_RAW/2);
            
            // 7 raw units is roughly 1 mV
            vDir    [s][c] = (lcg() & 1) ? 7 : -7;
            // 8 raw units is roughly 0.1 °C
            tDir    [s][c] = (lcg() & 1) ? 8 : -8;
        }
    }
}

// ────────────────────────────────────────────────────────────
void loop() {
    // ── Step voltages / temps ─────────────────────────────────
    for (int s = 0; s < NUM_SEG; s++) {
        for (int c = 0; c < NUM_CELLS; c++) {
            // Voltage drift
            voltages[s][c] += vDir[s][c];
            if (voltages[s][c] > V_NOM_RAW + V_SPREAD_RAW/2) vDir[s][c] = -7;
            if (voltages[s][c] < V_NOM_RAW - V_SPREAD_RAW/2) vDir[s][c] =  7;

            // Temp drift
            temps[s][c] += tDir[s][c];
            if (temps[s][c] > T_NOM_RAW + T_SPREAD_RAW/2) tDir[s][c] = -8;
            if (temps[s][c] < T_NOM_RAW - T_SPREAD_RAW/2) tDir[s][c] =  8;
        }
    }

    // ── Step current ─────────────────────────────────────────
    int current_a10 = random(40, 81);

    // ── Build flag bytes ─────────────────────────────────────
    static uint8_t activeFaultSeg = 0;

    // Change to a new random segment every time the phase changes (every 10 frames)
    if (frameCounter % 10 == 0) {
        activeFaultSeg = randRange(0, NUM_SEG - 1);
    }

    uint8_t phase = (frameCounter / 10) % 8;
    frameCounter++;

    uint8_t flags[NUM_SEG][NUM_CELLS];
    memset(flags, 0, sizeof(flags));

    // Apply the current fault phase to the chosen cell in ONE random segment
    if (phase == 1) flags[activeFaultSeg][FAULT_CELL] = (1 << 7); // OV
    if (phase == 2) flags[activeFaultSeg][FAULT_CELL] = (1 << 6); // UV
    if (phase == 3) flags[activeFaultSeg][FAULT_CELL] = (1 << 5); // OT
    if (phase == 4) flags[activeFaultSeg][FAULT_CELL] = (1 << 4); // UT
    if (phase == 5) flags[activeFaultSeg][FAULT_CELL] = (1 << 3); // OW
    if (phase == 6) flags[activeFaultSeg][FAULT_CELL] = (1 << 2); // OWT
    if (phase == 7) flags[activeFaultSeg][FAULT_CELL] = (1 << 1); // B
    

    // ── Send the frame ────────────────────────────────────────

    // Header
    Serial.write(0xAA);
    Serial.write(0x55);

    // Flags: 126 bytes
    for (int s = 0; s < NUM_SEG; s++) {
        for (int c = 0; c < NUM_CELLS; c++) {
            Serial.write(flags[s][c]);
        }
    }

    // Voltages: 252 bytes (int16 big-endian, raw ADC values)
    for (int s = 0; s < NUM_SEG; s++) {
        for (int c = 0; c < NUM_CELLS; c++) {
            int16_t send_v = voltages[s][c];
            
            // INJECT VOLTAGE FAULTS (override the drifting value for this frame)
            if (s == activeFaultSeg && c == FAULT_CELL) {
                if (phase == 1) send_v = 18666; // OV -> forces 4.3V
                if (phase == 2) send_v = 8000;  // UV -> forces 2.7V
            }
            
            writeI16BE(send_v);
        }
    }

    // Temperatures: 252 bytes (int16 big-endian, raw ADC values)
    for (int s = 0; s < NUM_SEG; s++) {
        for (int c = 0; c < NUM_CELLS; c++) {
            int16_t send_t = temps[s][c];
            
            // INJECT TEMPERATURE FAULTS (override the drifting value for this frame)
            if (s == activeFaultSeg && c == FAULT_CELL) {
                if (phase == 3) send_t = -133;  // OT -> forces 65.0°C
                if (phase == 4) send_t = 4866;  // UT -> forces -5.0°C
            }
            
            writeI16BE(send_t);
        }
    }

    // Current: 2 bytes  (int16 big-endian, A × 10)
    writeI16BE(current_a10);

    Serial.flush();   // ensure all bytes are sent before sleeping
    delay(FRAME_INTERVAL_MS);
}
