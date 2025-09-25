"""
Analyze Hz rate of CSV files
"""

import csv
from datetime import datetime

def analyze_csv_hz(file_path):
    """Analyze recording frequency of CSV file"""

    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        timestamps = []

        for row in reader:
            # Parse timestamp
            ts = datetime.fromisoformat(row['timestamp'])
            timestamps.append(ts)

    if len(timestamps) < 2:
        print(f"Not enough data in {file_path}")
        return

    # Calculate duration and frequency
    start_time = timestamps[0]
    end_time = timestamps[-1]
    duration = (end_time - start_time).total_seconds()

    # Calculate Hz
    num_samples = len(timestamps)
    avg_hz = num_samples / duration if duration > 0 else 0

    # Analyze intervals
    intervals = []
    for i in range(1, len(timestamps)):
        interval = (timestamps[i] - timestamps[i-1]).total_seconds()
        intervals.append(interval)

    # Statistics
    min_interval = min(intervals) if intervals else 0
    max_interval = max(intervals) if intervals else 0
    avg_interval = sum(intervals) / len(intervals) if intervals else 0

    return {
        'file': file_path.split('\\')[-1],
        'samples': num_samples,
        'duration': duration,
        'avg_hz': avg_hz,
        'min_interval_ms': min_interval * 1000,
        'max_interval_ms': max_interval * 1000,
        'avg_interval_ms': avg_interval * 1000,
        'start_time': start_time,
        'end_time': end_time
    }

# Analyze both files
print("=" * 80)
print("CSV RECORDING FREQUENCY ANALYSIS")
print("=" * 80)

# Raw IMU/GPS data
raw_file = r"C:\ST\IMU_GPS_LOGGER\logs\20250918_185117_raw_imu_gps_data.csv"
print("\n1. RAW IMU/GPS DATA:")
print("-" * 40)

raw_stats = analyze_csv_hz(raw_file)
if raw_stats:
    print(f"File: {raw_stats['file']}")
    print(f"Total samples: {raw_stats['samples']:,}")
    print(f"Duration: {raw_stats['duration']:.2f} seconds")
    print(f"Average Hz: {raw_stats['avg_hz']:.1f} Hz")
    print(f"Interval range: {raw_stats['min_interval_ms']:.2f} - {raw_stats['max_interval_ms']:.2f} ms")
    print(f"Average interval: {raw_stats['avg_interval_ms']:.2f} ms")

    # Check if meeting 104Hz target
    if raw_stats['avg_hz'] >= 104:
        print(f"✓ Meets 104Hz target ({raw_stats['avg_hz']:.1f} Hz)")
    else:
        print(f"✗ Below 104Hz target ({raw_stats['avg_hz']:.1f} Hz)")

# ESKF data
eskf_file = r"C:\ST\IMU_GPS_LOGGER\logs\20250918_185117_eskf_imu_gps_data.csv"
print("\n2. ESKF DATA:")
print("-" * 40)

eskf_stats = analyze_csv_hz(eskf_file)
if eskf_stats:
    print(f"File: {eskf_stats['file']}")
    print(f"Total samples: {eskf_stats['samples']:,}")
    print(f"Duration: {eskf_stats['duration']:.2f} seconds")
    print(f"Average Hz: {eskf_stats['avg_hz']:.1f} Hz")
    print(f"Interval range: {eskf_stats['min_interval_ms']:.2f} - {eskf_stats['max_interval_ms']:.2f} ms")
    print(f"Average interval: {eskf_stats['avg_interval_ms']:.2f} ms")

    # Check if meeting 104Hz target
    if eskf_stats['avg_hz'] >= 104:
        print(f"✓ Meets 104Hz target ({eskf_stats['avg_hz']:.1f} Hz)")
    else:
        if eskf_stats['avg_hz'] < 10:
            print(f"✗ ESKF still at low frequency ({eskf_stats['avg_hz']:.1f} Hz)")
            print("  → STM32 firmware needs rebuild after main.c modification")
        else:
            print(f"✗ Below 104Hz target ({eskf_stats['avg_hz']:.1f} Hz)")

# Comparison
print("\n" + "=" * 80)
print("COMPARISON:")
print("-" * 40)

if raw_stats and eskf_stats:
    print(f"Raw IMU Hz:  {raw_stats['avg_hz']:6.1f} Hz ({raw_stats['samples']:,} samples)")
    print(f"ESKF Hz:     {eskf_stats['avg_hz']:6.1f} Hz ({eskf_stats['samples']:,} samples)")

    ratio = eskf_stats['avg_hz'] / raw_stats['avg_hz'] if raw_stats['avg_hz'] > 0 else 0
    print(f"Ratio:       {ratio:.1%} (ESKF/RAW)")

    if ratio < 0.5:
        print("\n⚠️  ESKF frequency is much lower than IMU!")
        print("   This indicates STM32 firmware still outputs ESKF at reduced rate")
        print("   Solution: Rebuild and reflash STM32 after main.c modification")