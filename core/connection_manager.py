"""
Connection Manager - Handle serial port detection and verification
"""

import serial
import serial.tools.list_ports
import time
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import sys
sys.path.append('..')
import config

@dataclass
class PortInfo:
    """Serial port information"""
    device: str
    description: str
    vid: Optional[int]
    pid: Optional[int]
    is_stm32: bool

@dataclass
class ConnectionTestResult:
    """Connection test results"""
    success: bool
    reason: str
    data_rate: float
    has_imu: bool
    has_gps: bool
    sample_data: List[str]
    error: Optional[str] = None
    format_validity: float = 0.0

class ConnectionManager:
    """Manage serial port connection and verification"""

    def __init__(self):
        self.port = None
        self.baudrate = config.SERIAL_BAUDRATE
        self.connection = None
        self.is_verified = False
        self.last_data_time = None

    def scan_ports(self) -> List[PortInfo]:
        """Scan all available serial ports"""
        ports = []

        for port in serial.tools.list_ports.comports():
            # Check if STM32 based on description or VID/PID
            is_stm32 = False
            if port.description:
                stm32_keywords = ['STM32', 'Virtual COM', 'ST-Link', 'STMicroelectronics']
                is_stm32 = any(keyword in port.description for keyword in stm32_keywords)

            # STMicroelectronics VID = 0x0483
            if port.vid == 0x0483:
                is_stm32 = True

            port_info = PortInfo(
                device=port.device,
                description=port.description or "Unknown Device",
                vid=port.vid,
                pid=port.pid,
                is_stm32=is_stm32
            )
            ports.append(port_info)

        # Sort: STM32 devices first
        ports.sort(key=lambda x: (not x.is_stm32, x.device))

        return ports

    def test_connection(self, port: str, verbose: bool = True) -> ConnectionTestResult:
        """Test serial port connection"""

        # Stage 1: Try to open port
        try:
            ser = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=config.SERIAL_TIMEOUT,
                write_timeout=1.0
            )
            # Set buffer size
            try:
                ser.set_buffer_size(rx_size=config.SERIAL_BUFFER_SIZE, tx_size=config.SERIAL_BUFFER_SIZE)
            except:
                pass  # Some systems don't support buffer size setting

        except serial.SerialException as e:
            return ConnectionTestResult(
                success=False,
                reason="PORT_OPEN_FAILED",
                data_rate=0,
                has_imu=False,
                has_gps=False,
                sample_data=[]
            )

        # Stage 2: Receive data for test duration
        if verbose:
            print("Testing connection (3 seconds)...")

        start_time = time.time()
        received_lines = []

        while time.time() - start_time < config.CONNECTION_TEST_DURATION:
            if ser.in_waiting > 0:
                try:
                    data = ser.read(ser.in_waiting)
                    lines = data.decode('utf-8', errors='ignore').strip().split('\n')
                    received_lines.extend(lines)
                except:
                    pass
            time.sleep(0.001)  # 1ms delay

        ser.close()

        # Check if any data received
        if not received_lines:
            return ConnectionTestResult(
                success=False,
                reason="NO_DATA",
                data_rate=0,
                has_imu=False,
                has_gps=False,
                sample_data=[]
            )

        # Stage 3: Validate data format
        has_imu = self._check_imu_format(received_lines)
        has_gps = self._check_gps_format(received_lines)
        data_rate = len(received_lines) / config.CONNECTION_TEST_DURATION

        # Calculate format validity
        valid_lines = sum(1 for line in received_lines if has_imu or has_gps)
        format_validity = (valid_lines / len(received_lines) * 100) if received_lines else 0

        # Check if format is valid
        if not has_imu and not has_gps:
            return ConnectionTestResult(
                success=False,
                reason="INVALID_FORMAT",
                data_rate=data_rate,
                has_imu=False,
                has_gps=False,
                sample_data=received_lines[:5],
                format_validity=format_validity
            )

        # Check data rate
        if data_rate < config.MIN_ACCEPTABLE_HZ:
            reason = "LOW_DATA_RATE"
        else:
            reason = "OK"

        return ConnectionTestResult(
            success=True,
            reason=reason,
            data_rate=data_rate,
            has_imu=has_imu,
            has_gps=has_gps,
            sample_data=received_lines[:5],
            format_validity=format_validity
        )

    def _check_imu_format(self, lines: List[str]) -> bool:
        """Check if IMU data format is present"""
        for line in lines:
            if re.match(config.IMU_PATTERN, line):
                return True
            if re.match(config.DATA_PATTERN, line):
                return True
            # ESKF pattern check disabled - IMU/GPS only mode
            # if re.match(config.ESKF_PATTERN, line):
            #     return True
        return False

    def _check_gps_format(self, lines: List[str]) -> bool:
        """Check if GPS data format is present"""
        for line in lines:
            if re.match(config.GPS_PATTERN, line):
                return True
            if re.match(config.DATA_PATTERN, line):
                return True
        return False

    def verify_continuous_data(self, port: str, duration: float = 10.0) -> Tuple[bool, Dict]:
        """Verify continuous data reception"""
        try:
            ser = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=config.SERIAL_TIMEOUT
            )

            # Set buffer size
            try:
                ser.set_buffer_size(rx_size=config.SERIAL_BUFFER_SIZE, tx_size=config.SERIAL_BUFFER_SIZE)
            except:
                pass

            start_time = time.time()
            sample_times = []
            packet_count = 0
            gaps = []
            last_time = start_time

            while time.time() - start_time < duration:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    lines = data.decode('utf-8', errors='ignore').strip().split('\n')

                    current_time = time.time()
                    for line in lines:
                        if line:
                            packet_count += 1
                            sample_times.append(current_time)

                            # Check for gaps
                            gap = current_time - last_time
                            if gap > 0.02:  # More than 20ms gap
                                gaps.append(gap)
                            last_time = current_time

                time.sleep(0.001)

            ser.close()

            # Calculate statistics
            total_duration = time.time() - start_time
            avg_hz = packet_count / total_duration

            stats = {
                'packet_count': packet_count,
                'duration': total_duration,
                'average_hz': avg_hz,
                'gaps': len(gaps),
                'max_gap': max(gaps) if gaps else 0
            }

            success = avg_hz >= config.MIN_ACCEPTABLE_HZ and len(gaps) < 10

            return success, stats

        except Exception as e:
            return False, {'error': str(e)}

    def optimize_settings(self, port: str) -> None:
        """Optimize serial settings for maximum throughput"""
        if self.connection:
            # Try to set larger buffer
            try:
                self.connection.set_buffer_size(rx_size=131072, tx_size=4096)  # 128KB RX
                print("Buffer size increased to 128KB")
            except:
                pass

            # Reduce timeout even more
            self.connection.timeout = 0.0001  # 0.1ms

            # Clear any pending data
            self.connection.reset_input_buffer()
            self.connection.reset_output_buffer()