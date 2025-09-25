"""
IMU GPS Logger - Main Application
104Hz data logging system with real-time monitoring
"""

import sys
import os
import time
import signal
from datetime import datetime
from typing import Optional
try:
    import msvcrt  # Windows keyboard input
except ImportError:
    msvcrt = None  # Non-Windows systems

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from core.connection_manager import ConnectionManager
from core.serial_reader import OptimizedSerialReader
from core.csv_logger import CSVLogger
from core.data_validator import DataValidator
from core.performance_monitor import PerformanceMonitor

class IMUGPSLogger:
    """Main application for IMU/GPS data logging"""

    def __init__(self):
        """Initialize logger components"""
        self.connection_manager = ConnectionManager()
        self.serial_reader = None
        self.csv_logger = None
        self.data_validator = None
        self.performance_monitor = None

        # Control flags
        self.running = False
        self.connected = False
        self.confirmation_mode = False
        self.confirmation_start_time = 0
        self.last_confirmation_update = 0

        # Statistics
        self.total_lines_processed = 0
        self.valid_lines = 0

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\nShutdown signal received. Stopping...")
        self.stop_logging()
        sys.exit(0)

    def find_and_connect(self) -> bool:
        """Find STM32 device and connect

        Returns:
            True if connected successfully
        """
        print("=" * 60)
        print("IMU GPS LOGGER - 104Hz Data Recording System")
        print("=" * 60)

        # Scan for ports
        print("\nScanning for STM32 devices...")
        ports = self.connection_manager.scan_ports()

        if not ports:
            print("No serial ports found!")
            return False

        print(f"Found {len(ports)} port(s):")
        for i, port in enumerate(ports):
            print(f"  {i+1}. {port.device}: {port.description}")

        # Test each port
        print("\nTesting connections...")
        for port in ports:
            print(f"\nTesting {port.device}...")
            result = self.connection_manager.test_connection(port.device, verbose=False)

            if result.success:
                print(f"  SUCCESS: {result.data_rate:.1f} Hz")
                print(f"  Format validity: {result.format_validity:.1f}%")

                # Use this port
                self.serial_reader = OptimizedSerialReader(
                    port=port.device,
                    baudrate=config.SERIAL_BAUDRATE
                )

                if self.serial_reader.connect():
                    print(f"\nConnected to {port.device}")
                    self.connected = True
                    return True
            else:
                print(f"  Failed: {result.error}")

        print("\nNo valid STM32 device found!")
        return False

    def initialize_components(self):
        """Initialize logging components"""
        print("\nInitializing components...")

        # CSV Logger
        self.csv_logger = CSVLogger(log_dir=config.LOG_DIRECTORY)

        # Data Validator
        self.data_validator = DataValidator()

        # Performance Monitor
        self.performance_monitor = PerformanceMonitor(target_hz=config.TARGET_HZ)

        print("  CSV Logger: Ready")
        print("  Data Validator: Ready")
        print("  Performance Monitor: Ready")

    def start_logging(self):
        """Start data logging"""
        if not self.connected:
            print("Error: Not connected to device!")
            return

        # Initialize components
        self.initialize_components()

        # Start CSV logging
        raw_file, eskf_file = self.csv_logger.start_logging()

        # Start performance monitoring
        self.performance_monitor.start_monitoring()

        # Reset validator
        self.data_validator.reset_statistics()

        print("\n" + "=" * 60)
        print("LOGGING STARTED")
        print("=" * 60)
        print(f"Target rate: {config.TARGET_HZ} Hz")
        print(f"Press ANY KEY to stop logging")
        print("-" * 60)

        self.running = True
        self._run_logging_loop()

    def _check_keyboard_input(self):
        """Check for keyboard input and handle termination confirmation"""
        if not msvcrt:
            return False  # No keyboard support on non-Windows

        # Check if any key is pressed
        if msvcrt.kbhit():
            key = msvcrt.getch()

            if not self.confirmation_mode:
                # First key press - enter confirmation mode
                self.confirmation_mode = True
                self.confirmation_start_time = time.time()
                self.last_confirmation_update = time.time()

                # Clear current line and show confirmation
                print(f"\n\n{'='*60}")
                print("⚠️  TERMINATION CONFIRMATION")
                print("="*60)
                print("정말 종료하시겠습니까?")
                print("5초 안에 아무 키나 한 번 더 누르면 종료됩니다.")
                print("5초 후 이 메시지가 사라지고 녹화가 계속됩니다...")
                print("📊 녹화는 계속 진행 중입니다...")
                print("="*60)
                print()  # Empty line for status updates
                return False
            else:
                # Second key press within confirmation period - terminate
                print(f"\n\n✅ 종료 확인됨. 데이터를 저장 중...")
                return True

        # Check confirmation timeout and update countdown
        if self.confirmation_mode:
            elapsed = time.time() - self.confirmation_start_time
            current_time = time.time()

            if elapsed >= 5.0:
                # Timeout - cancel termination
                self.confirmation_mode = False
                print(f"\n\n{'='*60}")
                print("❌ 확인 모드 종료. 녹화는 계속 진행 중입니다.")
                print("="*60)
                return False
            else:
                # Update countdown every 0.1 seconds
                if current_time - getattr(self, 'last_confirmation_update', 0) >= 0.1:
                    remaining = 5.0 - elapsed
                    # Use \r to overwrite the countdown line
                    print(f"\r⏱️  종료까지 {remaining:.1f}초... (아무 키나 누르면 즉시 종료)                    ", end="", flush=True)
                    self.last_confirmation_update = current_time

        return False

    def _run_logging_loop(self):
        """Main logging loop"""
        last_display = time.time()
        last_status = time.time()

        try:
            while self.running:
                # Check for keyboard termination
                if self._check_keyboard_input():
                    print("\n\n사용자 요청으로 종료합니다...")
                    break

                # Read batch
                batch = self.serial_reader.read_batch()

                if batch:
                    # Get batch timestamp
                    batch_timestamp = datetime.now()

                    # Validate all lines
                    for line in batch:
                        self.total_lines_processed += 1
                        validation = self.data_validator.validate_line(line)
                        if validation.is_valid:
                            self.valid_lines += 1

                    # Process batch with distributed timestamps
                    self.csv_logger.add_batch_lines(batch, batch_timestamp)

                    # Process ESKF data separately (DISABLED - IMU/GPS only mode)
                    # for line in batch:
                    #     if line.startswith("ESKF:"):
                    #         # ESKF gets its own timestamp
                    #         self.csv_logger.add_eskf_line(line, datetime.now())

                    # Update performance monitor
                    self.performance_monitor.record_sample(len(batch))

                # Display live status
                current_time = time.time()
                if current_time - last_display >= 1.0:
                    status = self.performance_monitor.format_live_status()
                    buffer_status = self.csv_logger.get_buffer_status()

                    if not self.confirmation_mode:
                        # Normal mode - overwrite current line
                        print(f"\r{status} | Buffer: {buffer_status['raw_buffer_size']}", end="")
                    else:
                        # Confirmation mode - show status on new line with prefix
                        print(f"\n📊 [녹화 중] {status} | Buffer: {buffer_status['raw_buffer_size']}")

                    last_display = current_time

                # Periodic detailed status (every 30 seconds, not during confirmation)
                if not self.confirmation_mode and current_time - last_status >= 30.0:
                    self._print_detailed_status()
                    last_status = current_time

                # Small sleep to prevent CPU spinning
                time.sleep(0.001)

        except KeyboardInterrupt:
            print("\n\nStopping logging...")
        except Exception as e:
            print(f"\n\nError during logging: {e}")
        finally:
            self.stop_logging()

    def _print_detailed_status(self):
        """Print detailed status information"""
        print("\n" + "-" * 60)

        # Validation statistics
        val_stats = self.data_validator.get_statistics()
        print(f"Validation: {val_stats['validity_rate']:.1f}% valid")
        print(f"  Stream distribution:", end="")
        for stream, count in val_stats['stream_counts'].items():
            if count > 0:
                print(f" {stream}:{count}", end="")
        print()

        # Performance check
        perf_status = self.performance_monitor.check_performance()
        for message in perf_status.values():
            print(f"  {message}")

        print("-" * 60)

    def stop_logging(self):
        """Stop logging and save data"""
        self.running = False

        if not self.connected:
            return

        print("\n\n" + "=" * 60)
        print("STOPPING LOGGER")
        print("=" * 60)

        # Disconnect serial
        if self.serial_reader:
            self.serial_reader.disconnect()
            print("Serial connection closed")

        # Save CSV files
        if self.csv_logger:
            print("\nSaving CSV files...")
            csv_stats = self.csv_logger.stop_logging()

            print("\nFiles saved:")
            if csv_stats['raw_file']:
                print(f"  Raw: {os.path.basename(csv_stats['raw_file'])}")
                print(f"       {csv_stats['raw_samples']} samples, {csv_stats['raw_file_size']/1024:.1f} KB")
            # ESKF output disabled - IMU/GPS only mode
            # if csv_stats['eskf_file'] and csv_stats['eskf_samples'] > 0:
            #     print(f"  ESKF: {os.path.basename(csv_stats['eskf_file'])}")
            #     print(f"        {csv_stats['eskf_samples']} samples, {csv_stats['eskf_file_size']/1024:.1f} KB")

        # Show performance summary
        if self.performance_monitor:
            self.performance_monitor.print_summary()

        # Show validation summary
        if self.data_validator:
            val_stats = self.data_validator.get_statistics()
            print("\n" + "=" * 60)
            print("VALIDATION SUMMARY")
            print("=" * 60)
            print(f"Total lines: {val_stats['total_lines']:,}")
            print(f"Valid lines: {val_stats['valid_lines']:,}")
            print(f"Invalid lines: {val_stats['invalid_lines']:,}")
            print(f"Validity rate: {val_stats['validity_rate']:.2f}%")

            print("\nStream distribution:")
            for stream, count in val_stats['stream_counts'].items():
                if count > 0:
                    percentage = (count / val_stats['total_lines'] * 100) if val_stats['total_lines'] > 0 else 0
                    print(f"  {stream}: {count:,} ({percentage:.1f}%)")

        print("\n" + "=" * 60)
        print("LOGGER STOPPED")
        print("=" * 60)

    def run_auto_mode(self, duration: Optional[float] = None):
        """Run in automatic mode

        Args:
            duration: Recording duration in seconds (None for continuous)
        """
        # Find and connect
        if not self.find_and_connect():
            print("\nFailed to connect to device!")
            return

        # Start logging
        print(f"\nStarting automatic logging...")
        if duration:
            print(f"Duration: {duration} seconds")
        else:
            print("Duration: Continuous (press Ctrl+C to stop)")

        self.initialize_components()

        # Start CSV logging
        raw_file, eskf_file = self.csv_logger.start_logging()

        # Start performance monitoring
        self.performance_monitor.start_monitoring()

        # Reset validator
        self.data_validator.reset_statistics()

        print("\n" + "=" * 60)
        print("LOGGING STARTED")
        print("=" * 60)

        self.running = True

        # Run with duration limit if specified
        start_time = time.time()
        last_display = time.time()

        try:
            while self.running:
                # Check duration
                if duration and (time.time() - start_time) >= duration:
                    print(f"\n\nDuration limit reached ({duration} seconds)")
                    break

                # Read batch
                batch = self.serial_reader.read_batch()

                if batch:
                    # Get batch timestamp
                    batch_timestamp = datetime.now()

                    # Validate all lines
                    for line in batch:
                        validation = self.data_validator.validate_line(line)

                    # Process batch with distributed timestamps
                    self.csv_logger.add_batch_lines(batch, batch_timestamp)

                    # Process ESKF data (DISABLED - IMU/GPS only mode)
                    # for line in batch:
                    #     if line.startswith("ESKF:"):
                    #         self.csv_logger.add_eskf_line(line, datetime.now())

                    # Update performance
                    self.performance_monitor.record_sample(len(batch))

                # Display status
                current_time = time.time()
                if current_time - last_display >= 1.0:
                    elapsed = current_time - start_time
                    status = self.performance_monitor.format_live_status()

                    if duration:
                        remaining = duration - elapsed
                        print(f"\r{status} | Remaining: {remaining:.1f}s", end="")
                    else:
                        print(f"\r{status}", end="")

                    last_display = current_time

                time.sleep(0.001)

        except KeyboardInterrupt:
            print("\n\nStopped by user")
        finally:
            self.stop_logging()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='IMU GPS Logger - 104Hz Data Recording System')
    parser.add_argument('-p', '--port', type=str, help='Serial port (e.g., COM3)')
    parser.add_argument('-d', '--duration', type=float, help='Recording duration in seconds')
    parser.add_argument('-a', '--auto', action='store_true', help='Auto-detect port and start')

    args = parser.parse_args()

    logger = IMUGPSLogger()

    if args.auto or not args.port:
        # Auto mode - find port and start
        logger.run_auto_mode(duration=args.duration)
    else:
        # Manual port specification
        logger.serial_reader = OptimizedSerialReader(
            port=args.port,
            baudrate=config.SERIAL_BAUDRATE
        )

        if logger.serial_reader.connect():
            logger.connected = True
            print(f"Connected to {args.port}")

            if args.duration:
                logger.run_auto_mode(duration=args.duration)
            else:
                logger.start_logging()
        else:
            print(f"Failed to connect to {args.port}")


if __name__ == "__main__":
    main()