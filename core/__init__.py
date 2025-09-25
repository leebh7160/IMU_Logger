"""
Core modules for IMU/GPS Data Logger
"""

from .connection_manager import ConnectionManager
from .serial_reader import OptimizedSerialReader

__all__ = [
    'ConnectionManager',
    'OptimizedSerialReader'
]