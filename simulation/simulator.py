"""Creating this to test the BMS code"""
# bms_simulator.py
import serial
import time
import random

# Replace with the FIRST port socat gave you
SIMULATOR_PORT = '/dev/pts/1'
BAUD_RATE = 9600

try:
    ser = serial.Serial(SIMULATOR_PORT, BAUD_RATE)
    print(f"Simulator connected to {SIMULATOR_PORT}")

    while True:
        # Generate realistic fluctuating BMS data
        voltage = round(random.uniform(11.5, 12.6), 2)  # Volts
        current = round(random.uniform(0.5, 5.0), 2)  # Amps
        temp = round(random.uniform(25.0, 35.0), 1)  # Celsius
        soc = round(random.uniform(80.0, 100.0), 1)  # State of Charge %

        # Format the data (assuming a simple comma-separated string)
        data_string = f"{voltage},{current},{temp},{soc}\n"

        # Send via UART
        ser.write(data_string.encode('utf-8'))
        print(f"Sent: {data_string.strip()}")

        time.sleep(1)  # Send data every second

except serial.SerialException as e:
    print(f"Error: {e}")