# IIT Roorkee Motorsports — BMS Monitor

A real-time Battery Management System (BMS) dashboard built in Python, used to monitor cells across a 9-segment, 14-cell-per-segment lithium battery pack.

---

## Overview

The app connects to a BMS over Serial and displays live:

- Cell voltage, temperature, and fault status
- Pack-level voltage and current
- Color-coded cell grid with hover tooltips

---

## File Structure

```
├── master.py            # Entry point — launches the GUI
├── gui_master.py        # All Tkinter UI logic (connection page + dashboard)
└── Serial_Com_ctrl.py   # Serial communication + UART frame parser
```

---

## Frame Format (Extended Mode — 634 bytes)

```
[0xAA 0x55] [Flags: 126 B] [Voltages: 252 B] [Temps: 252 B] [Current: 2 B]
```

| Field     | Size     | Format              | Description                          |
|-----------|----------|---------------------|--------------------------------------|
| Header    | 2 bytes  | `0xAA 0x55`         | Frame sync marker                    |
| Flags     | 126 bytes | 1 byte/cell        | Cell Fault Flags (Given Bellow)     |
| Voltages  | 252 bytes | Big-endian int16   | Raw ADC                    |
| Temps     | 252 bytes | Big-endian int16   | Raw ADC — converted via NTC LUT interpolation |
| Current   | 2 bytes  | Big-endian int16   | Amps × 10                   |

## Cell Fault Flags (per byte, MSB first)

| Bit | Flag | Meaning             |
|-----|------|---------------------|
| 7   | OV   | Over Voltage        |
| 6   | UV   | Under Voltage       |
| 5   | OT   | Over Temperature    |
| 4   | UT   | Under Temperature   |
| 3   | OW   | Open Wire (Voltage) |
| 2   | OWT  | Open Wire (Temp)    |
| 1   | B    | Balancing Active    |

---

## UI Features

- **Connection Page** — Select COM port and baud rate; auto-refreshes port list
- **Cell Colors**:
  - 🟢 Green — Normal
  - 🟠 Orange — Balancing active
  - 🔴 Red — Any fault (OV/UV/OT/UT/OW/OWT) or threshold exceeded
- **Hover Tooltips** — Shows voltage, temperature, and all flag states per cell
- **Stats Panel** — Pack voltage, current, voltage/temp extreme

---

## Getting Started

### Requirements

- Python 3.8+
- `pyserial`
- `tkinter`

### Install Dependencies

```bash
pip install pyserial
```

### Run

```bash
python master.py
```

---

## Authors

Made by **Agastya** and **Samarth** — IIT Roorkee Motorsports'29
