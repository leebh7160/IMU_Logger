"""
Data Validator - Validate and parse data from STM32
Supports multiple data streams: IMU, GPS, ESKF
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import sys
sys.path.append('..')
import config

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    stream_type: str  # IMU, GPS, ESKF, GPS_RAW, UNKNOWN
    data: Optional[Dict]
    error: Optional[str]

@dataclass
class IntegrityReport:
    """Data integrity analysis report"""
    total_lines: int
    valid_lines: int
    invalid_lines: int
    stream_counts: Dict[str, int]
    error_types: Dict[str, int]
    data_gaps: List[float]
    average_hz: float
    format_errors: List[str]

class DataValidator:
    """Validate and parse sensor data formats"""

    def __init__(self):
        # Compile regex patterns for better performance
        self.patterns = {
            'IMU': re.compile(config.IMU_PATTERN),
            'GPS': re.compile(config.GPS_PATTERN),
            'ESKF': re.compile(config.ESKF_PATTERN),
            'GPS_RAW': re.compile(r'GPS_RAW: (.+)'),
            'GPS_BYPASS': re.compile(r'GPS_BYPASS: (.+)')
        }

        # Statistics tracking
        self.reset_statistics()

    def reset_statistics(self):
        """Reset validation statistics"""
        self.total_lines = 0
        self.valid_lines = 0
        self.invalid_lines = 0
        self.stream_counts = {
            'IMU': 0,
            'GPS': 0,
            'ESKF': 0,
            'GPS_RAW': 0,
            'UNKNOWN': 0
        }
        self.error_types = {
            'empty_line': 0,
            'format_error': 0,
            'parse_error': 0,
            'range_error': 0
        }
        self.timestamps = []
        self.format_errors = []

    def validate_line(self, line: str) -> ValidationResult:
        """Validate and parse a single line

        Args:
            line: Raw line from serial

        Returns:
            ValidationResult with parsed data
        """
        self.total_lines += 1

        # Check for empty line
        if not line or not line.strip():
            self.invalid_lines += 1
            self.error_types['empty_line'] += 1
            return ValidationResult(False, 'UNKNOWN', None, 'Empty line')

        line = line.strip()

        # Try to match each pattern
        # Priority: IMU > GPS > ESKF > GPS_RAW

        # IMU stream
        if line.startswith("IMU:") and "ESKF:" not in line:
            result = self._validate_imu_stream(line)
            if result.is_valid:
                self.valid_lines += 1
                self.stream_counts['IMU'] += 1
            else:
                self.invalid_lines += 1
                self.error_types['format_error'] += 1
                self.format_errors.append(f"IMU format error: {line[:50]}...")
            return result

        # GPS stream
        elif line.startswith("GPS:") and "GPS_RAW" not in line:
            result = self._validate_gps_stream(line)
            if result.is_valid:
                self.valid_lines += 1
                self.stream_counts['GPS'] += 1
            else:
                self.invalid_lines += 1
                self.error_types['format_error'] += 1
                self.format_errors.append(f"GPS format error: {line[:50]}...")
            return result

        # ESKF stream
        #elif line.startswith("ESKF:"):
        #    result = self._validate_eskf_stream(line)
        #    if result.is_valid:
        #        self.valid_lines += 1
        #        self.stream_counts['ESKF'] += 1
        #    else:
        #        self.invalid_lines += 1
        #        self.error_types['format_error'] += 1
        #        self.format_errors.append(f"ESKF format error: {line[:50]}...")
        #    return result

        # GPS_RAW or GPS_BYPASS (NMEA data)
        elif line.startswith("GPS_RAW:") or line.startswith("GPS_BYPASS:"):
            self.valid_lines += 1
            self.stream_counts['GPS_RAW'] += 1
            return ValidationResult(True, 'GPS_RAW', {'raw': line}, None)

        # Unknown format
        else:
            self.invalid_lines += 1
            self.stream_counts['UNKNOWN'] += 1
            return ValidationResult(False, 'UNKNOWN', None, f'Unknown format: {line[:30]}')


    def _validate_imu_stream(self, line: str) -> ValidationResult:
        """Validate IMU stream format"""
        match = self.patterns['IMU'].match(line)
        if not match:
            return ValidationResult(False, 'IMU', None, 'Format mismatch')

        try:
            data = {
                'accelerometer': {
                    'x': float(match.group(1)),
                    'y': float(match.group(2)),
                    'z': float(match.group(3))
                },
                'gyroscope': {
                    'x': float(match.group(4)),
                    'y': float(match.group(5)),
                    'z': float(match.group(6))
                }
            }

            # Validate ranges
            if not self._validate_imu_ranges(data['accelerometer'], data['gyroscope']):
                return ValidationResult(False, 'IMU', None, 'IMU values out of range')

            return ValidationResult(True, 'IMU', data, None)

        except (ValueError, IndexError) as e:
            return ValidationResult(False, 'IMU', None, f'Parse error: {e}')

    def _validate_gps_stream(self, line: str) -> ValidationResult:
        """Validate GPS stream format"""
        match = self.patterns['GPS'].match(line)
        if not match:
            return ValidationResult(False, 'GPS', None, 'Format mismatch')

        try:
            data = {
                'gps': {
                    'latitude': float(match.group(1)),
                    'longitude': float(match.group(2)),
                    'status': match.group(3)
                }
            }

            # Validate GPS coordinates range
            lat = data['gps']['latitude']
            lng = data['gps']['longitude']
            if abs(lat) > 90 or abs(lng) > 180:
                if not (lat == 0 and lng == 0):  # Allow 0,0 for no fix
                    return ValidationResult(False, 'GPS', None, 'GPS coordinates out of range')

            return ValidationResult(True, 'GPS', data, None)

        except (ValueError, IndexError) as e:
            return ValidationResult(False, 'GPS', None, f'Parse error: {e}')

    def _validate_eskf_stream(self, line: str) -> ValidationResult:
        """Validate ESKF stream format"""
        # Simplified pattern for current ESKF format
        pattern = r'ESKF: IMU\[([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)\] Pos\[([-\d.]+),([-\d.]+),([-\d.]+)\] Att\[([-\d.]+),([-\d.]+)'
        match = re.match(pattern, line)

        if not match:
            return ValidationResult(False, 'ESKF', None, 'Format mismatch')

        try:
            data = {
                'accelerometer': {
                    'x': float(match.group(1)),
                    'y': float(match.group(2)),
                    'z': float(match.group(3))
                },
                'gyroscope': {
                    'x': float(match.group(4)),
                    'y': float(match.group(5)),
                    'z': float(match.group(6))
                },
                'position': {
                    'x': float(match.group(7)),
                    'y': float(match.group(8)),
                    'z': float(match.group(9))
                },
                'attitude': {
                    'roll': float(match.group(10)),
                    'pitch': float(match.group(11)),
                    'yaw': 0.0  # Sometimes cut off in data
                }
            }

            return ValidationResult(True, 'ESKF', data, None)

        except (ValueError, IndexError) as e:
            return ValidationResult(False, 'ESKF', None, f'Parse error: {e}')

    def _validate_imu_ranges(self, accel: Dict, gyro: Dict) -> bool:
        """Validate IMU sensor ranges

        Args:
            accel: Accelerometer data (g)
            gyro: Gyroscope data (dps)

        Returns:
            True if within reasonable ranges
        """
        # Accelerometer typical range: ±8g
        for axis in ['x', 'y', 'z']:
            if abs(accel[axis]) > 10.0:  # Allow some margin
                self.error_types['range_error'] += 1
                return False

        # Gyroscope typical range: ±500 dps
        for axis in ['x', 'y', 'z']:
            if abs(gyro[axis]) > 600.0:  # Allow some margin
                self.error_types['range_error'] += 1
                return False

        return True

    def check_data_integrity(self, lines: List[str], duration: float = None) -> IntegrityReport:
        """Check integrity of multiple data lines

        Args:
            lines: List of data lines
            duration: Optional duration in seconds

        Returns:
            IntegrityReport with analysis results
        """
        self.reset_statistics()

        # Process all lines
        for line in lines:
            self.validate_line(line)

        # Calculate data gaps (simplified - would need timestamps for accurate gaps)
        data_gaps = []

        # Calculate average Hz
        if duration and duration > 0:
            average_hz = self.valid_lines / duration
        else:
            average_hz = 0

        return IntegrityReport(
            total_lines=self.total_lines,
            valid_lines=self.valid_lines,
            invalid_lines=self.invalid_lines,
            stream_counts=self.stream_counts,
            error_types=self.error_types,
            data_gaps=data_gaps,
            average_hz=average_hz,
            format_errors=self.format_errors[:10]  # First 10 errors
        )

    def get_statistics(self) -> Dict:
        """Get current validation statistics"""
        validity_rate = (self.valid_lines / self.total_lines * 100) if self.total_lines > 0 else 0

        return {
            'total_lines': self.total_lines,
            'valid_lines': self.valid_lines,
            'invalid_lines': self.invalid_lines,
            'validity_rate': validity_rate,
            'stream_counts': self.stream_counts,
            'error_types': self.error_types
        }