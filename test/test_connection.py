"""
Test connection and data reception
"""

from core.connection_manager import ConnectionManager
import sys

def test_connection():
    print("=" * 60)
    print("CONNECTION TEST")
    print("=" * 60)

    # Create connection manager
    cm = ConnectionManager()

    # First scan ports
    print("\nScanning ports...")
    ports = cm.scan_ports()

    if not ports:
        print("No ports found!")
        return

    # Select port
    port_to_test = "COM3"  # or ports[0].device
    print(f"\nTesting connection to: {port_to_test}")
    print("-" * 40)

    # Test connection
    result = cm.test_connection(port_to_test, verbose=True)

    print("\n" + "=" * 40)
    print("TEST RESULTS:")
    print("-" * 40)
    print(f"Success: {result.success}")
    print(f"Reason: {result.reason}")
    print(f"Data rate: {result.data_rate:.1f} Hz")
    print(f"IMU data detected: {'Yes' if result.has_imu else 'No'}")
    print(f"GPS data detected: {'Yes' if result.has_gps else 'No'}")

    if result.sample_data:
        print(f"\nSample data (first 5 lines):")
        print("-" * 40)
        for i, line in enumerate(result.sample_data[:5]):
            print(f"{i+1}: {line[:100]}")  # Limit line length for display

    # Provide diagnosis
    print("\n" + "=" * 40)
    print("DIAGNOSIS:")
    print("-" * 40)

    if not result.success:
        if result.reason == "PORT_OPEN_FAILED":
            print("Cannot open port. Possible causes:")
            print("  - Port is used by another program")
            print("  - Wrong port selected")
            print("  - Permission issues")
        elif result.reason == "NO_DATA":
            print("No data received. Possible causes:")
            print("  - STM32 not running")
            print("  - Wrong baudrate (current: 115200)")
            print("  - Cable issue")
        elif result.reason == "INVALID_FORMAT":
            print("Invalid data format. Possible causes:")
            print("  - Wrong firmware on STM32")
            print("  - Different data format than expected")
    elif result.reason == "LOW_DATA_RATE":
        print(f"Warning: Low data rate ({result.data_rate:.1f} Hz)")
        print(f"Expected: 104 Hz")
        print("Possible causes:")
        print("  - STM32 running at lower rate")
        print("  - Serial communication bottleneck")
    else:
        print("Connection successful!")
        print(f"Receiving data at {result.data_rate:.1f} Hz")

if __name__ == "__main__":
    test_connection()