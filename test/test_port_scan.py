"""
Test port scanning functionality
"""

from core.connection_manager import ConnectionManager

def test_port_scan():
    print("=" * 60)
    print("PORT SCAN TEST")
    print("=" * 60)

    # Create connection manager
    cm = ConnectionManager()

    # Scan ports
    print("\nScanning for available serial ports...")
    ports = cm.scan_ports()

    if not ports:
        print("\nNo serial ports found!")
        print("Please check:")
        print("  - STM32 is connected via USB")
        print("  - Drivers are installed")
        print("  - Cable is working")
        return

    print(f"\nFound {len(ports)} port(s):")
    print("-" * 40)

    for i, port in enumerate(ports):
        # Mark STM32 devices
        marker = "[STM32]" if port.is_stm32 else "       "

        print(f"{marker} {i+1}. {port.device}")
        print(f"        Description: {port.description}")
        if port.vid and port.pid:
            print(f"        VID/PID: {hex(port.vid)}/{hex(port.pid)}")
        print()

    # Show recommended port
    stm32_ports = [p for p in ports if p.is_stm32]
    if stm32_ports:
        print(f"Recommended port: {stm32_ports[0].device}")
    else:
        print(f"No STM32 detected. First available port: {ports[0].device}")

if __name__ == "__main__":
    test_port_scan()