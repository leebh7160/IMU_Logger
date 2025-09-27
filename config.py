"""
Configuration settings for IMU/GPS Data Logger
"""

# Serial Configuration
SERIAL_PORT = None                # None for auto-detect, or specify "COM3"
SERIAL_BAUDRATE = 115200         # Baud rate for STM32
SERIAL_BUFFER_SIZE = 65536       # 65KB buffer size
SERIAL_TIMEOUT = 0.001            # 1ms timeout for non-blocking

# Performance Settings
TARGET_HZ = 104                   # Expected sampling rate from STM32
MIN_ACCEPTABLE_HZ = 95            # Warning threshold
POLLING_INTERVAL_MS = 1           # Main loop delay in milliseconds

# GPS Settings
GPS_COORDINATE_UPDATE_HZ = 1      # GPS coordinate update frequency (1Hz)

# Buffer Settings
MAX_MEMORY_BUFFER = 1000000       # Maximum samples in memory (about 160 seconds at 104Hz)
BATCH_READ_SIZE = 100             # Lines to read per batch

# Logging Settings
LOG_DIRECTORY = "./logs"          # Output directory for CSV files
CSV_ENCODING = "utf-8"            # File encoding
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S" # Format for log filenames

# Validation Settings
CONNECTION_TEST_DURATION = 3.0    # Seconds to test connection
VALIDATION_DURATION = 10.0        # Seconds for data validation
MIN_PACKETS_FOR_VALIDATION = 100  # Minimum packets needed for valid test

# Data Format Patterns (for validation)
IMU_PATTERN = r"IMU: Acc\[([-\d.]+),([-\d.]+),([-\d.]+)\] Gyro\[([-\d.]+),([-\d.]+),([-\d.]+)\]"
GPS_PATTERN = r"GPS: Lat\[([-\d.]+)\] Lng\[([-\d.]+)\] .*Status\[(VALID|SEARCHING)\]"
ESKF_PATTERN = r"ESKF: Pos\[([-\d.]+),([-\d.]+),([-\d.]+)\] Vel\[([-\d.]+),([-\d.]+),([-\d.]+)\] Att\[([-\d.]+),([-\d.]+),([-\d.]+)\]"