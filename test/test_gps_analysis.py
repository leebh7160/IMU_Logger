"""
Test GPS data reception and frequency analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.serial_reader import OptimizedSerialReader
import time
import re

def analyze_gps_data():
    print("=" * 60)
    print("GPS DATA ANALYSIS")
    print("=" * 60)

    # Create serial reader
    reader = OptimizedSerialReader(port="COM3", baudrate=115200)

    # Connect
    print("\nConnecting to COM3...")
    if not reader.connect():
        print("Failed to connect!")
        return

    print("Connected successfully!")
    print("-" * 40)

    # Test parameters
    test_duration = 20.0  # 20 seconds to see GPS updates

    # Data tracking
    imu_count = 0
    gps_count = 0
    data_count = 0
    eskf_count = 0
    gps_raw_count = 0

    gps_values = []  # Track GPS coordinates
    last_gps_lat = 0.0
    last_gps_lng = 0.0
    gps_changes = 0

    print(f"\nAnalyzing data streams for {test_duration} seconds...")
    print("Looking for GPS data...\n")

    start_time = time.time()
    last_display = start_time
    last_gps_time = 0

    try:
        while time.time() - start_time < test_duration:
            # Read batch
            batch = reader.read_batch()

            if batch:
                for line in batch:
                    # Count different data types
                    if line.startswith("IMU:") and "ESKF:" not in line:
                        imu_count += 1

                    elif line.startswith("GPS:"):
                        gps_count += 1
                        # Extract GPS coordinates
                        match = re.search(r'Lat\[([-\d.]+)\] Lng\[([-\d.]+)\]', line)
                        if match:
                            lat = float(match.group(1))
                            lng = float(match.group(2))
                            gps_values.append((time.time() - start_time, lat, lng))

                            # Check if GPS value changed
                            if lat != last_gps_lat or lng != last_gps_lng:
                                gps_changes += 1
                                last_gps_lat = lat
                                last_gps_lng = lng

                    elif line.startswith("DATA:"):
                        data_count += 1
                        # Extract GPS from DATA line
                        match = re.search(r'GPS\[([-\d.]+),([-\d.]+),(\d)\]', line)
                        if match:
                            lat = float(match.group(1))
                            lng = float(match.group(2))
                            status = int(match.group(3))

                            # Track if GPS coordinates in DATA stream change
                            if lat != last_gps_lat or lng != last_gps_lng:
                                if lat != 0 or lng != 0:  # Ignore 0,0
                                    gps_changes += 1
                                    last_gps_lat = lat
                                    last_gps_lng = lng

                    elif line.startswith("ESKF:"):
                        eskf_count += 1

                    elif line.startswith("GPS_RAW:") or line.startswith("GPS_BYPASS:"):
                        gps_raw_count += 1

            # Display status every 2 seconds
            current_time = time.time()
            if current_time - last_display >= 2.0:
                elapsed = current_time - start_time

                print(f"[{elapsed:.1f}s] Data count:")
                print(f"  IMU:  {imu_count:5d} ({imu_count/elapsed:.1f} Hz)")
                print(f"  GPS:  {gps_count:5d} ({gps_count/elapsed:.1f} Hz)")
                print(f"  DATA: {data_count:5d} ({data_count/elapsed:.1f} Hz)")
                print(f"  ESKF: {eskf_count:5d} ({eskf_count/elapsed:.1f} Hz)")

                if gps_values:
                    last_gps = gps_values[-1]
                    print(f"  Last GPS: Lat={last_gps[1]:.6f}, Lng={last_gps[2]:.6f}")

                print(f"  GPS value changes: {gps_changes}")
                print()

                last_display = current_time

            time.sleep(0.001)  # 1ms

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

    # Disconnect
    reader.disconnect()

    # Final analysis
    actual_duration = time.time() - start_time

    print("\n" + "=" * 60)
    print("FINAL ANALYSIS")
    print("=" * 60)

    print(f"\nTest duration: {actual_duration:.2f} seconds")
    print(f"\nData stream frequencies:")
    print(f"  IMU-only:  {imu_count:5d} samples ({imu_count/actual_duration:.1f} Hz)")
    print(f"  GPS-only:  {gps_count:5d} samples ({gps_count/actual_duration:.1f} Hz)")
    print(f"  DATA:      {data_count:5d} samples ({data_count/actual_duration:.1f} Hz)")
    print(f"  ESKF:      {eskf_count:5d} samples ({eskf_count/actual_duration:.1f} Hz)")
    print(f"  GPS_RAW:   {gps_raw_count:5d} samples")

    total_lines = imu_count + gps_count + data_count + eskf_count
    print(f"\nTotal data lines: {total_lines}")
    print(f"Overall data rate: {total_lines/actual_duration:.1f} Hz")

    # GPS analysis
    print(f"\n" + "-" * 40)
    print("GPS ANALYSIS:")
    print("-" * 40)

    if gps_values:
        print(f"GPS samples collected: {len(gps_values)}")
        print(f"GPS value changes: {gps_changes}")

        # Check GPS update intervals
        if len(gps_values) > 1:
            intervals = []
            for i in range(1, len(gps_values)):
                interval = gps_values[i][0] - gps_values[i-1][0]
                intervals.append(interval)

            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                print(f"Average GPS update interval: {avg_interval:.2f} seconds")
                print(f"GPS update frequency: {1/avg_interval:.1f} Hz" if avg_interval > 0 else "")

        # Show unique GPS values
        unique_coords = set((v[1], v[2]) for v in gps_values)
        print(f"\nUnique GPS coordinates seen: {len(unique_coords)}")
        for coord in list(unique_coords)[:5]:  # Show first 5
            print(f"  Lat={coord[0]:.6f}, Lng={coord[1]:.6f}")
    else:
        print("No GPS data detected")

    # Stream composition analysis
    print(f"\n" + "-" * 40)
    print("STREAM COMPOSITION:")
    print("-" * 40)

    if total_lines > 0:
        print(f"  IMU-only: {imu_count/total_lines*100:.1f}%")
        print(f"  GPS-only: {gps_count/total_lines*100:.1f}%")
        print(f"  DATA:     {data_count/total_lines*100:.1f}%")
        print(f"  ESKF:     {eskf_count/total_lines*100:.1f}%")

    # GPS status
    print(f"\n" + "-" * 40)
    print("GPS STATUS:")
    print("-" * 40)

    if gps_changes > 0:
        print("GPS is ACTIVE and updating")
    elif last_gps_lat == 0 and last_gps_lng == 0:
        print("GPS is SEARCHING (no fix yet)")
        print("Currently showing: 0.000000, 0.000000")
    else:
        print("GPS has a fix but position is static")
        print(f"Fixed position: {last_gps_lat:.6f}, {last_gps_lng:.6f}")

if __name__ == "__main__":
    analyze_gps_data()