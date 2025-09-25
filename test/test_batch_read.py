"""
Test batch reading functionality for 104Hz data collection
"""

from core.serial_reader import OptimizedSerialReader
import time
from collections import deque

def test_batch_reading():
    print("=" * 60)
    print("BATCH READING TEST")
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
    test_duration = 10.0  # 10 seconds test

    # Statistics tracking
    batch_sizes = []
    timestamps = deque(maxlen=1000)
    total_lines = 0
    empty_reads = 0
    max_batch = 0

    print(f"\nTesting batch reading for {test_duration} seconds...")
    print("Press Ctrl+C to stop early\n")

    start_time = time.time()
    last_display = start_time

    try:
        while time.time() - start_time < test_duration:
            # Read batch
            batch = reader.read_batch()

            if batch:
                # Record statistics
                batch_size = len(batch)
                batch_sizes.append(batch_size)
                total_lines += batch_size
                max_batch = max(max_batch, batch_size)

                # Add timestamps
                current_time = time.time()
                for _ in range(batch_size):
                    timestamps.append(current_time)

                # Display sample data occasionally
                if current_time - last_display >= 1.0:  # Every 1 second
                    # Calculate current Hz
                    if len(timestamps) > 1:
                        time_span = timestamps[-1] - timestamps[0]
                        current_hz = len(timestamps) / time_span if time_span > 0 else 0
                    else:
                        current_hz = 0

                    print(f"[{current_time - start_time:.1f}s] "
                          f"Batch: {batch_size} lines | "
                          f"Total: {total_lines} | "
                          f"Hz: {current_hz:.1f} | "
                          f"Max batch: {max_batch}")

                    # Show first line of batch as sample
                    if batch:
                        sample = batch[0][:80] if len(batch[0]) > 80 else batch[0]
                        print(f"  Sample: {sample}")

                    last_display = current_time
            else:
                empty_reads += 1

            # Small delay to prevent CPU hogging
            time.sleep(0.001)  # 1ms

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

    # Disconnect
    reader.disconnect()

    # Calculate final statistics
    actual_duration = time.time() - start_time

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    print(f"\nTest duration: {actual_duration:.2f} seconds")
    print(f"Total lines read: {total_lines}")
    print(f"Total batches: {len(batch_sizes)}")
    print(f"Empty reads: {empty_reads}")

    if batch_sizes:
        avg_batch = sum(batch_sizes) / len(batch_sizes)
        print(f"\nBatch size statistics:")
        print(f"  Average: {avg_batch:.1f} lines/batch")
        print(f"  Maximum: {max_batch} lines/batch")
        print(f"  Minimum: {min(batch_sizes)} lines/batch")

    # Calculate Hz
    actual_hz = total_lines / actual_duration
    print(f"\nData rate: {actual_hz:.1f} Hz")

    # Buffer status
    buffer_status = reader.get_buffer_status()
    print(f"\nBuffer statistics:")
    print(f"  Total bytes read: {buffer_status['total_bytes']:,}")
    print(f"  Total lines read: {buffer_status['total_lines']}")
    print(f"  Bytes per line avg: {buffer_status['total_bytes'] / buffer_status['total_lines']:.1f}" if buffer_status['total_lines'] > 0 else "")

    # Performance analysis
    print("\n" + "-" * 40)
    print("PERFORMANCE ANALYSIS:")
    print("-" * 40)

    if actual_hz >= 104:
        print(f"SUCCESS: Achieved {actual_hz:.1f} Hz (target: 104 Hz)")
    elif actual_hz >= 95:
        print(f"GOOD: {actual_hz:.1f} Hz is acceptable (target: 104 Hz)")
    else:
        print(f"WARNING: Low data rate {actual_hz:.1f} Hz (target: 104 Hz)")

    if max_batch > 20:
        print(f"NOTE: Large batches detected (max: {max_batch})")
        print("      This indicates buffering - data is accumulating")
        print("      Consider reading more frequently")

    efficiency = (len(batch_sizes) / (len(batch_sizes) + empty_reads)) * 100 if (len(batch_sizes) + empty_reads) > 0 else 0
    print(f"\nRead efficiency: {efficiency:.1f}% (non-empty reads)")

    if efficiency < 50:
        print("TIP: Low efficiency - consider reducing read frequency")

if __name__ == "__main__":
    test_batch_reading()