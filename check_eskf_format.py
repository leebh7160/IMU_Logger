"""
Check actual ESKF data format from STM32
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.serial_reader import OptimizedSerialReader
import time

def check_eskf():
    reader = OptimizedSerialReader(port="COM3", baudrate=115200)

    print("Connecting to COM3...")
    if not reader.connect():
        print("Failed to connect!")
        return

    print("Collecting ESKF data for 5 seconds...\n")

    eskf_samples = []
    start = time.time()

    while time.time() - start < 5:
        batch = reader.read_batch()
        if batch:
            for line in batch:
                if line.startswith("ESKF:") and len(eskf_samples) < 10:
                    eskf_samples.append(line)
        time.sleep(0.01)

    reader.disconnect()

    print("=" * 80)
    print("ESKF DATA SAMPLES:")
    print("-" * 80)
    for i, sample in enumerate(eskf_samples, 1):
        print(f"{i}. {sample}")

        # Parse and show components
        if "IMU[" in sample and "Pos[" in sample and "Att[" in sample:
            imu = sample.split("IMU[")[1].split("]")[0]
            pos = sample.split("Pos[")[1].split("]")[0]
            att = sample.split("Att[")[1].split("]")[0] if "Att[" in sample else "N/A"

            print(f"   IMU: [{imu}]")
            print(f"   Pos: [{pos}]")
            print(f"   Att: [{att}]")
            print()

if __name__ == "__main__":
    check_eskf()