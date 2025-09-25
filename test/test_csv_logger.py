"""
Test CSV Logger functionality with real data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.csv_logger import CSVLogger
from core.serial_reader import OptimizedSerialReader
import time
from datetime import datetime

def test_csv_logging():
    print("=" * 60)
    print("CSV LOGGER TEST")
    print("=" * 60)

    # Create CSV logger
    logger = CSVLogger()

    # Create serial reader
    reader = OptimizedSerialReader(port="COM3", baudrate=115200)

    # Connect to serial
    print("\nConnecting to COM3...")
    if not reader.connect():
        print("Failed to connect!")
        return

    print("Connected successfully!")

    # Start logging
    print("\n" + "-" * 40)
    print("Starting CSV logging...")
    raw_file, eskf_file = logger.start_logging()

    # Collect data for test period
    test_duration = 10.0  # 10 seconds
    print(f"\nCollecting data for {test_duration} seconds...")

    start_time = time.time()
    last_display = start_time
    batch_count = 0

    try:
        while time.time() - start_time < test_duration:
            # Read batch
            batch = reader.read_batch()

            if batch:
                batch_count += 1
                timestamp = datetime.now()

                # Add each line to logger
                for line in batch:
                    # Add raw data
                    logger.add_raw_line(line, timestamp)

                    # Add ESKF data if present
                    if line.startswith("ESKF:"):
                        logger.add_eskf_line(line, timestamp)

                # Display progress
                current_time = time.time()
                if current_time - last_display >= 1.0:
                    elapsed = current_time - start_time
                    status = logger.get_buffer_status()

                    print(f"[{elapsed:.1f}s] "
                          f"Samples: {status['total_samples']} | "
                          f"Raw buffer: {status['raw_buffer_size']} | "
                          f"ESKF buffer: {status['eskf_buffer_size']} | "
                          f"Memory: {status['memory_usage_mb']:.2f} MB")

                    last_display = current_time

            time.sleep(0.001)  # 1ms

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

    # Disconnect serial
    reader.disconnect()

    # Stop logging and save
    print("\n" + "-" * 40)
    print("Stopping logging and saving CSV files...")
    stats = logger.stop_logging()

    # Display results
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    print(f"\nLogging Statistics:")
    print(f"  Duration: {stats['duration_seconds']:.1f} seconds")
    print(f"  Total samples: {stats['total_samples']}")
    print(f"  Average Hz: {stats['average_hz']:.1f}")
    print(f"  Raw samples: {stats['raw_samples']}")
    print(f"  ESKF samples: {stats['eskf_samples']}")

    if stats['raw_file']:
        print(f"\nRaw CSV file:")
        print(f"  Path: {stats['raw_file']}")
        print(f"  Size: {stats['raw_file_size'] / 1024:.1f} KB")

        # Read and display first 5 lines
        if os.path.exists(stats['raw_file']):
            print(f"\n  First 5 data rows:")
            with open(stats['raw_file'], 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[1:6]):  # Skip header
                    parts = line.split(',')
                    if len(parts) >= 7:
                        print(f"    {i+1}. Time: {parts[0][:19]} | "
                              f"Acc: [{parts[1][:6]},{parts[2][:6]},{parts[3][:6]}] | "
                              f"Gyro: [{parts[4][:6]},{parts[5][:6]},{parts[6][:6]}]")

    if stats['eskf_file'] and stats['eskf_samples'] > 0:
        print(f"\nESKF CSV file:")
        print(f"  Path: {stats['eskf_file']}")
        print(f"  Size: {stats['eskf_file_size'] / 1024:.1f} KB")

    # Performance analysis
    print("\n" + "-" * 40)
    print("PERFORMANCE ANALYSIS:")
    print("-" * 40)

    if stats['average_hz'] >= 104:
        print(f"SUCCESS: Achieved {stats['average_hz']:.1f} Hz logging rate")
    elif stats['average_hz'] >= 95:
        print(f"GOOD: {stats['average_hz']:.1f} Hz is acceptable")
    else:
        print(f"WARNING: Low logging rate {stats['average_hz']:.1f} Hz")

    # CSV format validation
    print("\n" + "-" * 40)
    print("CSV FORMAT VALIDATION:")
    print("-" * 40)

    expected_columns = 15  # Backend format: timestamp + 14 data columns
    if os.path.exists(stats['raw_file']):
        with open(stats['raw_file'], 'r') as f:
            header = f.readline().strip()
            columns = header.split(',')
            print(f"  Header columns: {len(columns)}")
            print(f"  Expected: {expected_columns}")

            if len(columns) == expected_columns:
                print("  FORMAT: VALID - Compatible with backend")
            else:
                print("  FORMAT: INVALID - Column count mismatch")

            # Show column names
            print("\n  Column names:")
            for i, col in enumerate(columns):
                print(f"    {i+1}. {col}")

if __name__ == "__main__":
    test_csv_logging()