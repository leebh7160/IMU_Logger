"""
Test Performance Monitor functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.performance_monitor import PerformanceMonitor
from core.serial_reader import OptimizedSerialReader
import time

def test_performance_monitoring():
    print("=" * 60)
    print("PERFORMANCE MONITOR TEST")
    print("=" * 60)

    # Create monitor
    monitor = PerformanceMonitor(target_hz=104.0)

    # Test 1: Basic functionality
    print("\n1. Testing basic monitoring functions:")
    print("-" * 40)

    monitor.start_monitoring()

    # Simulate data collection
    print("Simulating data collection at various rates...")

    # Fast rate (>104 Hz)
    for i in range(50):
        monitor.record_sample()
        time.sleep(0.008)  # ~125 Hz

    metrics = monitor.get_metrics()
    print(f"\nAfter fast collection:")
    print(f"  Current Hz: {metrics.current_hz:.1f}")
    print(f"  Average Hz: {metrics.average_hz:.1f}")
    print(f"  Peak Hz: {metrics.peak_hz:.1f}")

    # Slow rate (<104 Hz)
    for i in range(50):
        monitor.record_sample()
        time.sleep(0.012)  # ~83 Hz

    metrics = monitor.get_metrics()
    print(f"\nAfter slow collection:")
    print(f"  Current Hz: {metrics.current_hz:.1f}")
    print(f"  Average Hz: {metrics.average_hz:.1f}")
    print(f"  Min Hz: {metrics.min_hz:.1f}")

    # Test 2: Real serial monitoring
    print("\n" + "=" * 60)
    print("2. Testing with real serial data:")
    print("-" * 40)

    reader = OptimizedSerialReader(port="COM3", baudrate=115200)

    print("Connecting to COM3...")
    if not reader.connect():
        print("Failed to connect! Skipping real data test.")
        return

    print("Connected! Monitoring performance for 10 seconds...")

    # Reset monitor
    monitor = PerformanceMonitor(target_hz=104.0)
    monitor.start_monitoring()

    # Monitor real data
    test_duration = 10.0
    start_time = time.time()
    last_display = start_time

    try:
        while time.time() - start_time < test_duration:
            batch = reader.read_batch()

            if batch:
                # Record batch
                monitor.record_sample(len(batch))
            else:
                # No data - potential drop
                monitor.record_drop()

            # Display live status
            current_time = time.time()
            if current_time - last_display >= 1.0:
                print(monitor.format_live_status())
                last_display = current_time

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

    reader.disconnect()

    # Show final summary
    monitor.print_summary()

    # Test 3: Performance checks
    print("\n" + "=" * 60)
    print("3. Testing performance checks:")
    print("-" * 40)

    status = monitor.check_performance()
    for category, message in status.items():
        print(f"{category.upper()}: {message}")

    # Test 4: Batch processing
    print("\n" + "=" * 60)
    print("4. Testing batch recording:")
    print("-" * 40)

    monitor = PerformanceMonitor(target_hz=104.0)
    monitor.start_monitoring()

    # Simulate batch processing
    print("Recording batches of different sizes...")
    batch_sizes = [5, 10, 15, 20, 25]

    for size in batch_sizes:
        monitor.record_sample(size)
        time.sleep(0.1)
        metrics = monitor.get_metrics()
        print(f"  Batch size {size}: {metrics.samples_total} total, {metrics.current_hz:.1f} Hz")

    print("\nFinal metrics after batch processing:")
    metrics = monitor.get_metrics()
    print(f"  Total samples: {metrics.samples_total}")
    print(f"  Average Hz: {metrics.average_hz:.1f}")
    print(f"  Memory usage: {metrics.memory_mb:.1f} MB")
    print(f"  CPU usage: {metrics.cpu_percent:.1f}%")

if __name__ == "__main__":
    test_performance_monitoring()