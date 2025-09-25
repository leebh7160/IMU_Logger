"""
Optimized Serial Reader - High-speed data collection for 104Hz
Based on backend improvements with batch processing
"""

import serial
import time
from typing import List, Dict, Optional, Union
from datetime import datetime
import sys
sys.path.append('..')
import config

class OptimizedSerialReader:
    """Optimized serial reader for 104Hz data collection"""

    def __init__(self, port: str = None, baudrate: int = None):
        self.port = port or config.SERIAL_PORT
        self.baudrate = baudrate or config.SERIAL_BAUDRATE
        self.serial_connection = None
        self.is_running = False
        self.incomplete_line = b''  # Buffer for incomplete lines
        self.total_bytes_read = 0
        self.total_lines_read = 0

    def connect(self, port: str = None, baudrate: int = None) -> bool:
        """Connect to serial port with optimized settings"""
        if port:
            self.port = port
        if baudrate:
            self.baudrate = baudrate

        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=config.SERIAL_TIMEOUT,  # 1ms timeout for non-blocking
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )

            # Increase buffer size to prevent data loss
            try:
                self.serial_connection.set_buffer_size(
                    rx_size=config.SERIAL_BUFFER_SIZE,
                    tx_size=config.SERIAL_BUFFER_SIZE
                )
            except:
                # Some systems don't support buffer size setting
                pass

            # Clear any existing data
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()

            self.is_running = True
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True

        except serial.SerialException as e:
            print(f"Serial connection error: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect serial port"""
        if self.serial_connection:
            self.is_running = False
            self.serial_connection.close()
            print("Serial connection closed")

    def read_batch(self) -> Union[List[str], None]:
        """
        Read all available data at once (batch processing)
        Returns list of complete lines or None if no data
        """
        if not self.serial_connection or not self.is_running:
            return None

        try:
            # Check if data is available
            if self.serial_connection.in_waiting > 0:
                # Non-blocking read of all available data
                available_data = self.serial_connection.read(self.serial_connection.in_waiting)
                self.total_bytes_read += len(available_data)

                # Combine with incomplete line from previous read
                data = self.incomplete_line + available_data

                # Split by newline and process complete lines
                lines = data.split(b'\n')

                # Keep last incomplete line for next iteration
                self.incomplete_line = lines[-1]

                # Process all complete lines
                results = []
                for line in lines[:-1]:  # All except the last (incomplete) line
                    try:
                        # Decode and strip whitespace
                        text = line.decode('utf-8', errors='ignore').strip()
                        if text:  # Only add non-empty lines
                            results.append(text)
                            self.total_lines_read += 1
                    except:
                        # Skip lines that can't be decoded
                        continue

                # Return results if any
                if results:
                    return results

        except serial.SerialException as e:
            print(f"Serial read error: {e}")
            self.is_running = False
            return None
        except Exception as e:
            print(f"Unexpected error in read_batch: {e}")
            return None

        return None

    def read_single(self) -> Optional[str]:
        """
        Read a single line (for compatibility)
        Uses batch reading internally but returns one line
        """
        batch = self.read_batch()
        if batch and len(batch) > 0:
            return batch[0]
        return None

    def get_buffer_status(self) -> Dict:
        """Get current buffer and connection status"""
        if not self.serial_connection:
            return {
                'connected': False,
                'in_waiting': 0,
                'total_bytes': 0,
                'total_lines': 0
            }

        return {
            'connected': self.is_running,
            'in_waiting': self.serial_connection.in_waiting if self.is_running else 0,
            'total_bytes': self.total_bytes_read,
            'total_lines': self.total_lines_read,
            'incomplete_buffer_size': len(self.incomplete_line)
        }

    def flush_buffers(self) -> None:
        """Clear all buffers"""
        if self.serial_connection and self.is_running:
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            self.incomplete_line = b''

    def send_command(self, command: str) -> bool:
        """Send command to device (for GPS configuration etc.)"""
        if not self.serial_connection or not self.is_running:
            return False

        try:
            if not command.endswith('\n'):
                command += '\r\n'
            self.serial_connection.write(command.encode('utf-8'))
            self.serial_connection.flush()
            return True
        except:
            return False

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.disconnect()