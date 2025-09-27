#!/usr/bin/env python3
"""
Simple serial debug reader to see raw STM32 output
"""
import serial
import time
import sys

def main():
    try:
        # Connect to STM32
        port = "COM3"
        baudrate = 115200

        print(f"Connecting to {port} at {baudrate} baud...")
        ser = serial.Serial(port, baudrate, timeout=1)

        print("Connected! Reading raw output for 10 seconds...")
        print("=" * 60)

        start_time = time.time()
        eskf_count = 0
        imu_count = 0

        while time.time() - start_time < 10:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"RAW: {line}")

                        # Count different types
                        if line.startswith("ESKF"):
                            eskf_count += 1
                        elif line.startswith("IMU"):
                            imu_count += 1

                except Exception as e:
                    print(f"Error reading line: {e}")

            time.sleep(0.001)

        print("=" * 60)
        print(f"Summary after 10 seconds:")
        print(f"ESKF lines: {eskf_count}")
        print(f"IMU lines: {imu_count}")

        ser.close()

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())