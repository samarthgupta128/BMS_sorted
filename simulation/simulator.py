import serial
import time
import random
import json

SIMULATOR_PORT = '/dev/pts/2'
BAUD_RATE = 9600

NUM_SEGMENTS = 14
CELLS_PER_SEGMENT = 9
TOTAL_CELLS = NUM_SEGMENTS * CELLS_PER_SEGMENT

def generate_frame():
    base_voltage = random.uniform(3.6, 3.9)
    voltages = [round(max(0.0, random.gauss(base_voltage, 0.03)), 3) for _ in range(TOTAL_CELLS)]
    temperatures = [round(random.uniform(25.0, 35.0), 1) for _ in range(TOTAL_CELLS)]
    balancing = [random.random() < 0.1 for _ in range(TOTAL_CELLS)]
    
    pack_voltage = sum(voltages)
    current = round(random.uniform(5.0, 15.0), 2)
    
    data = {
        "pack_voltage": round(pack_voltage, 2),
        "total_current": current,
        "peak_current": round(current * 1.5, 2),
        "temperature": round(sum(temperatures)/len(temperatures), 1),
        "soc": round(random.uniform(80.0, 100.0), 1),
        "soh": 98.5,
        "cycle_count": 142,
        "capacity": 55.0,
        "cell_voltages": voltages,
        "cell_temperatures": temperatures,
        "balancing": balancing,
        "alarms": {
            "over_voltage": any(v > 4.2 for v in voltages),
            "under_voltage": any(v < 3.0 for v in voltages),
            "over_temp": any(t > 60 for t in temperatures),
            "under_temp": any(t < 0 for t in temperatures),
            "over_current": current > 100,
            "open_wire": False,
            "open_wire_temp": False
        }
    }
    return data

def main():
    try:
        ser = serial.Serial(SIMULATOR_PORT, BAUD_RATE, timeout=1)
        print(f"Simulator connected to {SIMULATOR_PORT} @ {BAUD_RATE}bps")

        while True:
            frame = generate_frame()
            line = json.dumps(frame) + "\n"
            ser.write(line.encode('utf-8'))
            print("Sent JSON frame")
            time.sleep(1)

    except serial.SerialException as e:
        print(f"Serial error: {e}")

if __name__ == '__main__':
    main()
