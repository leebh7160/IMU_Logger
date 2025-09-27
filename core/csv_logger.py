"""
CSV Logger - Efficient memory buffering and CSV file writing
Core functionality for 104Hz data logging
Uses same CSV format as backend for compatibility
"""

import csv
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import sys
sys.path.append('..')
import config

class CSVLogger:
    """High-performance CSV logger with memory buffering"""

    def __init__(self, log_dir: str = None):
        """Initialize CSV logger

        Args:
            log_dir: Directory for log files (default from config)
        """
        self.log_dir = log_dir or config.LOG_DIRECTORY
        self.raw_buffer = []      # Raw IMU/GPS data buffer
        self.eskf_buffer = []     # ESKF processed data buffer

        # Statistics
        self.start_time = None
        self.end_time = None
        self.total_samples = 0

        # File paths
        self.raw_filename = None
        self.eskf_filename = None

        # Timing for distributed timestamps
        self.expected_interval_ms = 1000.0 / config.TARGET_HZ  # ~9.615ms for 104Hz

        # CSV headers - Enhanced 16-field format
        self.headers = [
            'timestamp',
            'accel_x', 'accel_y', 'accel_z',
            'gyro_x', 'gyro_y', 'gyro_z',
            'utc_time',
            'gps_available', 'gps_lat', 'gps_lng', 'gps_alt',
            'speed_kmh', 'heading', 'nav_status',
            'satellites'
        ]

        # ESKF headers (16-column format, identical to IMU headers) - ENABLED
        self.eskf_headers = [
            'timestamp',                        # Same as IMU
            'accel_x', 'accel_y', 'accel_z',   # ESKF Position (mapped to accel columns)
            'gyro_x', 'gyro_y', 'gyro_z',      # ESKF Velocity (mapped to gyro columns)
            'utc_time',                         # Same GPS data as IMU
            'gps_available', 'gps_lat', 'gps_lng', 'gps_alt',  # Same GPS data as IMU
            'speed_kmh', 'heading', 'nav_status',               # Same GPS data as IMU
            'satellites'                        # Same GPS data as IMU
        ]

        # GPS tracking (no longer needed for CSV, but kept for internal logic)
        self.last_valid_gps = {
            'lat': 0.0,
            'lng': 0.0,
            'alt': 0.0
        }

        # GPS coordinate update limiting (1Hz)
        self.last_gps_coordinate_update = 0.0

        # GPS update flag (True only when GPS coordinates are actually updated)
        self.gps_just_updated = False

        # GPS connection status (separate from coordinate updates)
        self.gps_connection_status = False

        # Satellite count from NMEA messages
        self.current_satellite_count = 0

        # Enhanced GPS data from NMEA parsing
        self.utc_time = ""              # UTC time from GNRMC
        self.gps_altitude = 0.0         # Altitude from GNGGA
        self.gps_speed_kmh = 0.0        # Speed from GPS stream (converted to km/h)
        self.gps_heading = 0.0          # Heading from GNRMC
        self.nav_status = 0             # Navigation status from GPS stream

        # Ensure log directory exists
        self._ensure_log_directory()

    def _ensure_log_directory(self) -> None:
        """Create log directory if it doesn't exist"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            print(f"Created log directory: {self.log_dir}")

    def start_logging(self) -> Tuple[str, str]:
        """Start new logging session

        Returns:
            Tuple of (raw_filename, eskf_filename)
        """
        # Clear buffers
        self.raw_buffer.clear()
        self.eskf_buffer.clear()

        # Reset statistics
        self.start_time = datetime.now()
        self.end_time = None
        self.total_samples = 0

        # Generate filenames - same format as backend
        timestamp = self.start_time.strftime(config.TIMESTAMP_FORMAT)
        self.raw_filename = os.path.join(self.log_dir, f"{timestamp}_raw_imu_gps_data.csv")
        self.eskf_filename = os.path.join(self.log_dir, f"{timestamp}_eskf_imu_gps_data.csv")

        print(f"Logging started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Raw data will be saved to: {os.path.basename(self.raw_filename)}")
        # ESKF logging disabled - IMU/GPS only mode
        # print(f"ESKF data will be saved to: {os.path.basename(self.eskf_filename)}")

        return self.raw_filename, self.eskf_filename

    def add_raw_line(self, line: str, timestamp: Optional[datetime] = None) -> None:
        """Add raw line from serial (parse and add to buffer)

        Args:
            line: Raw line from serial port
            timestamp: Optional timestamp (uses current time if None)
        """
        import re

        if not timestamp:
            timestamp = datetime.now()

        # Parse IMU-only stream
        if line.startswith("IMU:") and "ESKF:" not in line:
            match = re.match(r'IMU: Acc\[([-\d.]+),([-\d.]+),([-\d.]+)\] Gyro\[([-\d.]+),([-\d.]+),([-\d.]+)\]', line)
            if match:
                row = [
                    timestamp.isoformat(),
                    float(match.group(1)),  # accel_x
                    float(match.group(2)),  # accel_y
                    float(match.group(3)),  # accel_z
                    float(match.group(4)),  # gyro_x
                    float(match.group(5)),  # gyro_y
                    float(match.group(6)),  # gyro_z
                    self.utc_time,          # utc_time from NMEA
                    False,                  # gps_available (False for IMU-only)
                    '',                     # gps_lat (no GPS in IMU-only)
                    '',                     # gps_lng (no GPS in IMU-only)
                    self.gps_altitude,      # gps_alt from NMEA
                    0.0,                    # speed_kmh (no GPS in IMU-only)
                    self.gps_heading,       # heading from NMEA
                    0,                      # nav_status (0 = initializing when no GPS)
                    self.current_satellite_count  # satellites from NMEA
                ]
                self.raw_buffer.append(row)
                self.total_samples += 1

        # Parse GPS-only stream (legacy - not used in current implementation)
        elif line.startswith("GPS:") and "GPS_RAW:" not in line:
            # New GPS format: GPS: Lat[37.123456] Lng[127.123456] Speed[12.5] NavState[1] Status[VALID]
            match = re.match(r'GPS: Lat\[([-\d.]+)\] Lng\[([-\d.]+)\] Speed\[([-\d.]+)\] NavState\[(\d)\] Status\[(VALID|SEARCHING)\]', line)
            if match:
                gps_lat = float(match.group(1))
                gps_lng = float(match.group(2))
                gps_speed_knots = float(match.group(3))
                nav_state = int(match.group(4))
                gps_valid = match.group(5) == "VALID"

                # Convert speed from knots to km/h (1 knot = 1.852 km/h)
                self.gps_speed_kmh = gps_speed_knots * 1.852

                # Update navigation status
                self.nav_status = nav_state

                # Update last valid GPS
                if gps_valid and (gps_lat != 0 or gps_lng != 0):
                    self.last_valid_gps['lat'] = gps_lat
                    self.last_valid_gps['lng'] = gps_lng

                # For GPS-only lines, we don't have IMU data
                # Could optionally skip or use last known IMU values

    def add_eskf_line(self, line: str, timestamp: Optional[datetime] = None) -> None:
        """Add ESKF line to buffer

        Args:
            line: ESKF line from serial
            timestamp: Optional timestamp
        """
        import re

        if not timestamp:
            timestamp = datetime.now()

        if line.startswith("ESKF:"):
            # Parse NEW ESKF format: ESKF: Pos[x,y,z] Vel[x,y,z] Att[roll,pitch,yaw]
            match = re.match(config.ESKF_PATTERN, line)
            if match:
                # Extract ESKF data: Position, Velocity, Attitude
                pos_x, pos_y, pos_z = float(match.group(1)), float(match.group(2)), float(match.group(3))
                vel_x, vel_y, vel_z = float(match.group(4)), float(match.group(5)), float(match.group(6))
                roll, pitch, yaw = float(match.group(7)), float(match.group(8)), float(match.group(9))

                # Use same GPS state as IMU CSV for consistency
                current_gps_available = self.gps_connection_status if hasattr(self, 'gps_connection_status') else False
                current_gps_lat = self.current_gps_status.get('lat', '') if (hasattr(self, 'current_gps_status') and self.gps_just_updated) else ''
                current_gps_lng = self.current_gps_status.get('lng', '') if (hasattr(self, 'current_gps_status') and self.gps_just_updated) else ''
                current_gps_alt = self.current_gps_status.get('alt', 0.0) if (hasattr(self, 'current_gps_status') and self.gps_just_updated) else 0.0
                current_satellites = getattr(self, 'current_satellite_count', 0)

                # Build ESKF row with 16 columns (same structure as IMU)
                row = [
                    timestamp.isoformat(),  # timestamp
                    pos_x, pos_y, pos_z,    # Position → accel_x,y,z columns
                    vel_x, vel_y, vel_z,    # Velocity → gyro_x,y,z columns
                    getattr(self, 'utc_time', ''),           # utc_time (same GPS data)
                    current_gps_available,                   # gps_available
                    current_gps_lat,                        # gps_lat
                    current_gps_lng,                        # gps_lng
                    current_gps_alt,                        # gps_alt
                    getattr(self, 'gps_speed_kmh', 0.0),    # speed_kmh (same GPS data)
                    getattr(self, 'gps_heading', 0.0),      # heading (same GPS data)
                    getattr(self, 'nav_status', ''),        # nav_status (same GPS data)
                    current_satellites                       # satellites
                ]
                self.eskf_buffer.append(row)

    def stop_logging(self) -> Dict:
        """Stop logging and save buffers to CSV files

        Returns:
            Dictionary with logging statistics
        """
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0

        # Save raw data
        raw_saved = self._save_csv(self.raw_filename, self.headers, self.raw_buffer)

        # Save ESKF data (ENABLED - Full IMU/GPS/ESKF mode)
        eskf_saved = False
        if len(self.eskf_buffer) > 0:
            eskf_saved = self._save_csv(self.eskf_filename, self.eskf_headers, self.eskf_buffer)

        # Calculate statistics
        stats = {
            'duration_seconds': duration,
            'total_samples': self.total_samples,
            'average_hz': self.total_samples / duration if duration > 0 else 0,
            'raw_samples': len(self.raw_buffer),
            'eskf_samples': len(self.eskf_buffer),
            'raw_file': self.raw_filename if raw_saved else None,
            'eskf_file': self.eskf_filename if eskf_saved else None,
            'raw_file_size': os.path.getsize(self.raw_filename) if raw_saved and os.path.exists(self.raw_filename) else 0,
            'eskf_file_size': os.path.getsize(self.eskf_filename) if eskf_saved and os.path.exists(self.eskf_filename) else 0
        }

        print(f"\nLogging stopped at {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Total samples: {self.total_samples}")
        print(f"Average rate: {stats['average_hz']:.1f} Hz")

        if raw_saved:
            print(f"Raw data saved: {os.path.basename(self.raw_filename)} ({stats['raw_file_size']/1024:.1f} KB)")

        # ESKF saving disabled - IMU/GPS only mode
        # if eskf_saved:
        #     print(f"ESKF data saved: {os.path.basename(self.eskf_filename)} ({stats['eskf_file_size']/1024:.1f} KB)")

        # Clear buffers after saving
        self.raw_buffer.clear()
        self.eskf_buffer.clear()

        return stats

    def _save_csv(self, filename: str, headers: List[str], buffer: List[List]) -> bool:
        """Save buffer to CSV file

        Args:
            filename: Output filename
            headers: CSV headers
            buffer: Data buffer

        Returns:
            True if saved successfully
        """
        if not buffer:
            print(f"No data to save for {os.path.basename(filename)}")
            return False

        try:
            with open(filename, 'w', newline='', encoding=config.CSV_ENCODING) as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(buffer)

            return True

        except Exception as e:
            print(f"Error saving CSV {filename}: {e}")
            return False

    def add_batch_lines(self, lines: List[str], batch_timestamp: Optional[datetime] = None) -> None:
        """Add batch of lines - IMU generates CSV rows at 100Hz, GPS updates state

        Args:
            lines: List of raw lines from serial
            batch_timestamp: Base timestamp for the batch
        """
        if not lines:
            return

        from datetime import timedelta
        import re

        if not batch_timestamp:
            batch_timestamp = datetime.now()

        # Calculate time interval for 104Hz IMU sampling
        interval = timedelta(microseconds=self.expected_interval_ms * 1000)

        # Initialize global timing on first batch
        if not hasattr(self, 'global_sample_counter'):
            self.global_sample_counter = 0
            self.first_batch_timestamp = batch_timestamp

        # First pass: Process GPS and GPS_RAW lines to update GPS state
        for line in lines:
            if line.startswith("GPS:") or line.startswith("GPS_RAW:") or line.startswith("$CSIDR"):
                self._process_line(line, batch_timestamp)  # Update GPS state only

        # Second pass: Process IMU lines with globally continuous timestamps
        imu_lines = [line for line in lines if line.startswith("IMU:") and "ESKF:" not in line]

        for line in imu_lines:
            # Calculate globally continuous timestamp from first batch (104Hz uniform spacing)
            timestamp = self.first_batch_timestamp + (interval * self.global_sample_counter)
            self._process_line(line, timestamp)
            self.global_sample_counter += 1

        # Third pass: Process ESKF lines with globally continuous timestamps (same as IMU)
        eskf_lines = [line for line in lines if line.startswith("ESKF:")]

        # Initialize ESKF timing if not exists
        if not hasattr(self, 'eskf_sample_counter'):
            self.eskf_sample_counter = 0

        for line in eskf_lines:
            # Calculate globally continuous timestamp for ESKF (104Hz uniform spacing like IMU)
            timestamp = self.first_batch_timestamp + (interval * self.eskf_sample_counter)
            self.add_eskf_line(line, timestamp)
            self.eskf_sample_counter += 1

        # Ignore DATA stream to prevent duplication
        # DATA stream processing is disabled to avoid duplicate IMU data

    def _process_line(self, line: str, timestamp: datetime) -> None:
        """Process a single line - IMU generates CSV rows, GPS updates state only"""
        import re

        # Parse IMU stream - GENERATES CSV ROWS (100Hz)
        if line.startswith("IMU:") and "ESKF:" not in line:
            match = re.match(r'IMU: Acc\[([-\d.]+),([-\d.]+),([-\d.]+)\] Gyro\[([-\d.]+),([-\d.]+),([-\d.]+)\]', line)
            if match:
                # GPS available shows real-time connection status
                current_gps_available = self.gps_connection_status

                # GPS coordinates only when actually updated (1Hz intervals)
                current_gps_lat = self.current_gps_status.get('lat', '') if (hasattr(self, 'current_gps_status') and self.gps_just_updated) else ''
                current_gps_lng = self.current_gps_status.get('lng', '') if (hasattr(self, 'current_gps_status') and self.gps_just_updated) else ''
                current_gps_alt = self.current_gps_status.get('alt', 0.0) if (hasattr(self, 'current_gps_status') and self.gps_just_updated) else 0.0
                current_satellites = self.current_satellite_count  # Use current satellite count from NMEA

                # Reset GPS update flag after using it
                self.gps_just_updated = False

                row = [
                    timestamp.isoformat(),
                    float(match.group(1)),  # accel_x
                    float(match.group(2)),  # accel_y
                    float(match.group(3)),  # accel_z
                    float(match.group(4)),  # gyro_x
                    float(match.group(5)),  # gyro_y
                    float(match.group(6)),  # gyro_z
                    self.utc_time,          # utc_time from NMEA
                    current_gps_available,  # gps_available (True/False)
                    current_gps_lat,        # gps_lat
                    current_gps_lng,        # gps_lng
                    current_gps_alt,        # gps_alt
                    self.gps_speed_kmh,     # speed_kmh from GPS stream
                    self.gps_heading,       # heading from NMEA
                    self.nav_status,        # nav_status from GPS stream
                    current_satellites      # satellites
                ]
                self.raw_buffer.append(row)
                self.total_samples += 1

        # Parse GPS stream - UPDATE STATE ONLY (no CSV row generation)
        elif line.startswith("GPS:") and "GPS_RAW:" not in line:
            import time
            # Enhanced GPS format: GPS: Lat[37.123456] Lng[127.123456] Speed[12.5] NavState[1] Status[VALID]
            match = re.match(r'GPS: Lat\[([-\d.]+)\] Lng\[([-\d.]+)\] Speed\[([-\d.]+)\] NavState\[(\d)\] Status\[(VALID|SEARCHING)\]', line)
            if match:
                gps_lat = float(match.group(1))
                gps_lng = float(match.group(2))
                gps_speed_knots = float(match.group(3))
                nav_state = int(match.group(4))
                gps_valid = match.group(5) == "VALID"

                # Convert speed from knots to km/h and update navigation status
                self.gps_speed_kmh = gps_speed_knots * 1.852
                self.nav_status = nav_state

                # Initialize current GPS status if not exists
                if not hasattr(self, 'current_gps_status'):
                    self.current_gps_status = {'available': False, 'lat': '', 'lng': '', 'alt': 0.0, 'satellites': 0}

                # ALWAYS update GPS connection status (real-time)
                self.gps_connection_status = gps_valid

                # Check if we should update GPS coordinates (1Hz limited)
                current_time = time.time()
                gps_update_interval = 1.0 / config.GPS_COORDINATE_UPDATE_HZ
                should_update_coordinates = current_time - self.last_gps_coordinate_update >= gps_update_interval

                if should_update_coordinates and gps_valid and (gps_lat != 0 or gps_lng != 0):
                    # Update GPS coordinates (1Hz limited)
                    self.current_gps_status['lat'] = gps_lat
                    self.current_gps_status['lng'] = gps_lng
                    self.current_gps_status['alt'] = self.gps_altitude  # Use altitude from GNGGA
                    self.current_gps_status['satellites'] = self.current_satellite_count  # Use satellites from GNGGA

                    # Update last valid GPS
                    self.last_valid_gps['lat'] = gps_lat
                    self.last_valid_gps['lng'] = gps_lng
                    self.last_valid_gps['alt'] = self.gps_altitude

                    # Set flag that GPS was just updated
                    self.gps_just_updated = True
                    self.last_gps_coordinate_update = current_time

        # Parse GPS_RAW NMEA messages for enhanced data
        elif line.startswith("GPS_RAW:"):
            nmea_data = line[9:].strip()  # Remove "GPS_RAW: " prefix
            if nmea_data.startswith("$GNGGA"):
                # Parse GNGGA message for satellite count and altitude
                self._parse_gngga_satellites(nmea_data)
            elif nmea_data.startswith("$GNRMC"):
                # Parse GNRMC message for UTC time and heading
                self._parse_gnrmc_data(nmea_data)

        # Parse $CSIDR messages for comprehensive navigation data
        elif line.startswith("$CSIDR"):
            self._parse_csidr_message(line)


    def _parse_gngga_satellites(self, nmea_message: str) -> None:
        """Parse GNGGA NMEA message to extract satellite count and altitude

        GNGGA Format: $GNGGA,time,lat,lat_dir,lng,lng_dir,quality,satellites,hdop,alt,alt_unit,geoid,geoid_unit,dgps_age,dgps_id*checksum
        Example: $GNGGA,123519,3712.3456,N,12712.3456,E,1,08,0.9,545.4,M,46.9,M,,*47
                                                           ↑       ↑    ↑
                                                    Field 7: satellites
                                                           Field 9: altitude
                                                               Field 10: unit (M)
        """
        try:
            fields = nmea_message.split(',')

            # Extract satellite count (Field 7)
            if len(fields) > 7 and fields[7]:
                satellite_count = int(fields[7])
                self.current_satellite_count = satellite_count

            # Extract altitude (Field 9)
            if len(fields) > 9 and fields[9]:
                altitude = float(fields[9])
                self.gps_altitude = altitude

            # Optional: debug output
            # print(f"GPS_GNGGA: {satellite_count} satellites, altitude {altitude}m")
        except (ValueError, IndexError):
            # Ignore malformed NMEA messages
            pass

    def _parse_gnrmc_data(self, nmea_message: str) -> None:
        """Parse GNRMC NMEA message to extract UTC time and heading

        GNRMC Format: $GNRMC,time,status,lat,lat_dir,lng,lng_dir,speed,heading,date,mag_var,mag_var_dir*checksum
        Example: $GNRMC,123519,A,3712.3456,N,12712.3456,E,12.5,180.0,230394,000.0,0*43
                    0     1   2      3    4      5     6   7    8      9    10  11
                         ↑                                ↑    ↑
                   Field 1: UTC time (HHMMSS)
                                                   Field 7: speed (knots)
                                                        Field 8: heading (degrees)
        """
        try:
            fields = nmea_message.split(',')

            # Extract UTC time (Field 1) - format HHMMSS
            if len(fields) > 1 and fields[1]:
                utc_time_raw = fields[1]
                if len(utc_time_raw) >= 6:
                    # Format: HHMMSS.ss -> HH:MM:SS
                    hours = utc_time_raw[:2]
                    minutes = utc_time_raw[2:4]
                    seconds = utc_time_raw[4:6]
                    self.utc_time = f"{hours}:{minutes}:{seconds}"

            # Extract heading (Field 8) - degrees
            if len(fields) > 8 and fields[8]:
                heading = float(fields[8])
                self.gps_heading = heading

            # Optional: debug output
            # print(f"GPS_GNRMC: UTC {self.utc_time}, heading {self.gps_heading}°")
        except (ValueError, IndexError):
            # Ignore malformed NMEA messages
            pass

    def _parse_csidr_message(self, csidr_message: str) -> None:
        """Parse $CSIDR message for comprehensive navigation data

        $CSIDR Format: $CSIDR,HHMMSS.ss,DDMM.MMMMM,N/S,DDDMM.MMMMM,E/W,ALT,SPD,HDG,STATUS*CS
        Example: $CSIDR,123456.78,3712.34567,N,12712.34567,E,145.2,65.5,270.5,1*CS
        """
        try:
            # Remove checksum part if present
            if '*' in csidr_message:
                csidr_data = csidr_message.split('*')[0]
            else:
                csidr_data = csidr_message

            # Split by comma
            fields = csidr_data.split(',')

            if len(fields) >= 10 and fields[0] == '$CSIDR':
                # Extract UTC time (Field 1) - format HHMMSS.ss
                utc_time_raw = fields[1]
                if len(utc_time_raw) >= 6:
                    hours = utc_time_raw[:2]
                    minutes = utc_time_raw[2:4]
                    seconds = utc_time_raw[4:]
                    self.utc_time = f"{hours}:{minutes}:{seconds}"

                # Extract coordinates (Fields 2-5)
                lat_nmea = fields[2]  # DDMM.MMMMM
                lat_dir = fields[3]   # N/S
                lng_nmea = fields[4]  # DDDMM.MMMMM
                lng_dir = fields[5]   # E/W

                # Convert NMEA coordinates to decimal degrees
                if len(lat_nmea) >= 4:
                    lat_deg = int(lat_nmea[:2])
                    lat_min = float(lat_nmea[2:])
                    latitude = lat_deg + lat_min / 60.0
                    if lat_dir == 'S':
                        latitude = -latitude

                if len(lng_nmea) >= 5:
                    lng_deg = int(lng_nmea[:3])
                    lng_min = float(lng_nmea[3:])
                    longitude = lng_deg + lng_min / 60.0
                    if lng_dir == 'W':
                        longitude = -longitude

                # Extract other fields
                altitude = float(fields[6]) if fields[6] else 0.0
                speed_kmh = float(fields[7]) if fields[7] else 0.0
                heading = float(fields[8]) if fields[8] else 0.0
                nav_status = int(fields[9]) if fields[9] else 0

                # Update internal state with CSIDR data
                self.gps_altitude = altitude
                self.gps_speed_kmh = speed_kmh
                self.gps_heading = heading
                self.nav_status = nav_status

                # Update GPS position if coordinates are valid
                if 'latitude' in locals() and 'longitude' in locals():
                    if not hasattr(self, 'current_gps_status'):
                        self.current_gps_status = {'available': False, 'lat': '', 'lng': '', 'alt': 0.0, 'satellites': 0}

                    self.current_gps_status['lat'] = latitude
                    self.current_gps_status['lng'] = longitude
                    self.current_gps_status['alt'] = altitude
                    self.gps_connection_status = True

                    # Set GPS update flag
                    self.gps_just_updated = True

                # Optional: debug output
                # print(f"CSIDR: UTC {self.utc_time}, Lat {latitude:.6f}, Lng {longitude:.6f}, Alt {altitude}m, Speed {speed_kmh}km/h, Heading {heading}°, Status {nav_status}")

        except (ValueError, IndexError):
            # Ignore malformed CSIDR messages
            pass

    def get_buffer_status(self) -> Dict:
        """Get current buffer status

        Returns:
            Dictionary with buffer information
        """
        return {
            'raw_buffer_size': len(self.raw_buffer),
            'eskf_buffer_size': len(self.eskf_buffer),
            'total_samples': self.total_samples,
            'memory_usage_mb': (len(self.raw_buffer) + len(self.eskf_buffer)) * 100 / 1024 / 1024  # Rough estimate
        }