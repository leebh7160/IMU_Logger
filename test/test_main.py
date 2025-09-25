"""
Test Main Application Integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import threading
from main import IMUGPSLogger

def test_main_application():
    print("=" * 60)
    print("MAIN APPLICATION TEST")
    print("=" * 60)

    # Test 1: Component initialization
    print("\n1. Testing component initialization:")
    print("-" * 40)

    logger = IMUGPSLogger()
    print("Logger instance created")

    # Test port scanning
    print("\nTesting port detection...")
    ports = logger.connection_manager.scan_ports()
    print(f"Found {len(ports)} port(s)")

    for port in ports:
        print(f"  - {port.device}: {port.description}")

    # Test 2: Auto mode with duration
    print("\n" + "=" * 60)
    print("2. Testing auto mode with 15 second duration:")
    print("-" * 40)

    print("Starting auto mode test...")
    logger.run_auto_mode(duration=15.0)

    print("\nAuto mode test completed")

    # Test 3: Check generated files
    print("\n" + "=" * 60)
    print("3. Checking generated files:")
    print("-" * 40)

    log_dir = "logs"
    if os.path.exists(log_dir):
        files = os.listdir(log_dir)
        csv_files = [f for f in files if f.endswith('.csv')]

        print(f"Found {len(csv_files)} CSV file(s):")
        for file in csv_files[-4:]:  # Show last 4 files
            file_path = os.path.join(log_dir, file)
            size = os.path.getsize(file_path) / 1024
            print(f"  - {file} ({size:.1f} KB)")

            # Check file content
            with open(file_path, 'r') as f:
                lines = f.readlines()
                print(f"    Lines: {len(lines)}")
                if len(lines) > 1:
                    headers = lines[0].strip().split(',')
                    print(f"    Columns: {len(headers)}")

if __name__ == "__main__":
    test_main_application()