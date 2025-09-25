"""
Test Data Validator functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_validator import DataValidator
from core.serial_reader import OptimizedSerialReader
import time

def test_data_validation():
    print("=" * 60)
    print("DATA VALIDATOR TEST")
    print("=" * 60)

    # Create validator
    validator = DataValidator()

    # Test sample data lines
    print("\n1. Testing sample data formats:")
    print("-" * 40)

    test_lines = [
        "IMU: Acc[0.101,-0.003,0.231] Gyro[0.280,-0.560,-0.411]",
        "DATA: IMU[0.101,-0.003,0.231,0.280,-0.560,-0.411] GPS[37.421684,126.887044,1]",
        "GPS: Lat[37.421684] Lng[126.887044] Status[VALID]",
        "ESKF: IMU[0.101,-0.003,0.231,0.280,-0.560,-0.411] Pos[0.10,-0.01,8.42] Att[0.3,-0.2",
        "GPS_RAW: $GNRMC,123456.00,A,3725.301,N,12653.223,E,0.5,45.2",
        "Invalid line format",
        ""
    ]

    for line in test_lines:
        result = validator.validate_line(line)
        print(f"Line: {line[:50]}...")
        print(f"  Valid: {result.is_valid}")
        print(f"  Type: {result.stream_type}")
        if result.error:
            print(f"  Error: {result.error}")
        print()

    # Get statistics
    stats = validator.get_statistics()
    print("Validation Statistics:")
    print(f"  Total lines: {stats['total_lines']}")
    print(f"  Valid lines: {stats['valid_lines']}")
    print(f"  Invalid lines: {stats['invalid_lines']}")
    print(f"  Validity rate: {stats['validity_rate']:.1f}%")
    print(f"  Stream counts: {stats['stream_counts']}")
    print(f"  Error types: {stats['error_types']}")

    # Test with real serial data
    print("\n" + "=" * 60)
    print("2. Testing with real serial data:")
    print("-" * 40)

    # Connect to serial
    reader = OptimizedSerialReader(port="COM3", baudrate=115200)

    print("Connecting to COM3...")
    if not reader.connect():
        print("Failed to connect!")
        return

    print("Connected! Collecting data for 5 seconds...")

    # Reset validator
    validator.reset_statistics()

    # Collect data
    all_lines = []
    start_time = time.time()

    while time.time() - start_time < 5.0:
        batch = reader.read_batch()
        if batch:
            all_lines.extend(batch)
            for line in batch:
                validator.validate_line(line)
        time.sleep(0.001)

    duration = time.time() - start_time
    reader.disconnect()

    # Check integrity
    print(f"\nCollected {len(all_lines)} lines in {duration:.1f} seconds")

    integrity = validator.check_data_integrity(all_lines, duration)

    print("\n" + "-" * 40)
    print("INTEGRITY REPORT:")
    print("-" * 40)
    print(f"Total lines: {integrity.total_lines}")
    print(f"Valid lines: {integrity.valid_lines}")
    print(f"Invalid lines: {integrity.invalid_lines}")
    print(f"Average Hz: {integrity.average_hz:.1f}")

    print(f"\nStream distribution:")
    for stream_type, count in integrity.stream_counts.items():
        if count > 0:
            percentage = count / integrity.total_lines * 100
            print(f"  {stream_type}: {count} ({percentage:.1f}%)")

    print(f"\nError types:")
    for error_type, count in integrity.error_types.items():
        if count > 0:
            print(f"  {error_type}: {count}")

    if integrity.format_errors:
        print(f"\nFormat errors (first 5):")
        for i, error in enumerate(integrity.format_errors[:5]):
            print(f"  {i+1}. {error}")

    # Performance analysis
    print("\n" + "=" * 60)
    print("PERFORMANCE ANALYSIS:")
    print("-" * 40)

    validity_rate = (integrity.valid_lines / integrity.total_lines * 100) if integrity.total_lines > 0 else 0

    if validity_rate >= 99:
        print(f"EXCELLENT: {validity_rate:.1f}% data validity")
    elif validity_rate >= 95:
        print(f"GOOD: {validity_rate:.1f}% data validity")
    elif validity_rate >= 90:
        print(f"ACCEPTABLE: {validity_rate:.1f}% data validity")
    else:
        print(f"WARNING: Low validity rate {validity_rate:.1f}%")

    if integrity.average_hz >= 100:
        print(f"Data rate: {integrity.average_hz:.1f} Hz - OPTIMAL")
    else:
        print(f"Data rate: {integrity.average_hz:.1f} Hz - Below target")

if __name__ == "__main__":
    test_data_validation()