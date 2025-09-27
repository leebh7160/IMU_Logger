"""
Performance Monitor - Real-time performance tracking and analysis
Monitors data rates, buffer health, and system performance
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import deque
import psutil
import os

@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    current_hz: float
    average_hz: float
    peak_hz: float
    min_hz: float
    buffer_usage: float
    memory_mb: float
    cpu_percent: float
    samples_total: int
    samples_per_second: List[int]
    data_drops: int
    uptime_seconds: float
    gps_status: str
    satellite_count: int

class PerformanceMonitor:
    """Monitor and analyze system performance"""

    def __init__(self, target_hz: float = 104.0, window_size: int = 10):
        """Initialize performance monitor

        Args:
            target_hz: Target data rate in Hz
            window_size: Moving average window size in seconds
        """
        self.target_hz = target_hz
        self.window_size = window_size

        # Performance tracking
        self.start_time = None
        self.last_sample_time = None
        self.sample_times = deque(maxlen=1000)  # Last 1000 samples
        self.samples_per_second = deque(maxlen=window_size)

        # Statistics
        self.total_samples = 0
        self.data_drops = 0
        self.peak_hz = 0.0
        self.min_hz = float('inf')

        # Process monitoring
        self.process = psutil.Process(os.getpid())

        # GPS status tracking
        self.gps_status = "UNKNOWN"
        self.satellite_count = 0

    def start_monitoring(self) -> None:
        """Start performance monitoring"""
        self.start_time = time.time()
        self.last_sample_time = self.start_time
        self.total_samples = 0
        self.data_drops = 0
        self.sample_times.clear()
        self.samples_per_second.clear()

        print(f"Performance monitoring started. Target: {self.target_hz} Hz")

    def record_sample(self, batch_size: int = 1) -> None:
        """Record data sample(s)

        Args:
            batch_size: Number of samples in batch
        """
        current_time = time.time()

        if self.last_sample_time:
            # Track inter-sample timing
            delta = current_time - self.last_sample_time
            if delta > 0:
                instant_hz = batch_size / delta
                self.sample_times.append(instant_hz)

                # Update peaks
                if instant_hz > self.peak_hz:
                    self.peak_hz = instant_hz
                if instant_hz < self.min_hz and instant_hz > 0:
                    self.min_hz = instant_hz

        self.last_sample_time = current_time
        self.total_samples += batch_size

    def record_drop(self, count: int = 1) -> None:
        """Record dropped data

        Args:
            count: Number of dropped samples
        """
        self.data_drops += count

    def update_gps_status(self, gps_connected: bool, satellite_count: int) -> None:
        """Update GPS status information

        Args:
            gps_connected: GPS connection status
            satellite_count: Number of satellites
        """
        if gps_connected:
            if satellite_count >= 4:
                self.gps_status = "FIXED"
            elif satellite_count > 0:
                self.gps_status = "SEARCHING"
            else:
                self.gps_status = "NO_SATS"
        else:
            self.gps_status = "DISCONNECTED"

        self.satellite_count = satellite_count

    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics

        Returns:
            PerformanceMetrics with current statistics
        """
        current_time = time.time()

        if not self.start_time:
            return PerformanceMetrics(
                current_hz=0, average_hz=0, peak_hz=0, min_hz=0,
                buffer_usage=0, memory_mb=0, cpu_percent=0,
                samples_total=0, samples_per_second=[],
                data_drops=0, uptime_seconds=0,
                gps_status="UNKNOWN", satellite_count=0
            )

        uptime = current_time - self.start_time

        # Calculate current Hz (from recent samples)
        if self.sample_times:
            recent_samples = list(self.sample_times)[-10:]
            current_hz = sum(recent_samples) / len(recent_samples) if recent_samples else 0
        else:
            current_hz = 0

        # Calculate average Hz
        average_hz = self.total_samples / uptime if uptime > 0 else 0

        # Get system metrics
        try:
            memory_mb = self.process.memory_info().rss / 1024 / 1024
            cpu_percent = self.process.cpu_percent()
        except:
            memory_mb = 0
            cpu_percent = 0

        # Buffer usage estimation (would need actual buffer reference)
        buffer_usage = 0  # Placeholder

        return PerformanceMetrics(
            current_hz=current_hz,
            average_hz=average_hz,
            peak_hz=self.peak_hz,
            min_hz=self.min_hz if self.min_hz != float('inf') else 0,
            buffer_usage=buffer_usage,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            samples_total=self.total_samples,
            samples_per_second=list(self.samples_per_second),
            data_drops=self.data_drops,
            uptime_seconds=uptime,
            gps_status=self.gps_status,
            satellite_count=self.satellite_count
        )

    def check_performance(self) -> Dict[str, str]:
        """Check performance against targets

        Returns:
            Dictionary with performance status messages
        """
        metrics = self.get_metrics()
        status = {}

        # Data rate check
        if metrics.average_hz >= self.target_hz:
            status['rate'] = f"OPTIMAL: {metrics.average_hz:.1f} Hz >= {self.target_hz} Hz target"
        elif metrics.average_hz >= self.target_hz * 0.95:
            status['rate'] = f"GOOD: {metrics.average_hz:.1f} Hz (95% of target)"
        elif metrics.average_hz >= self.target_hz * 0.90:
            status['rate'] = f"ACCEPTABLE: {metrics.average_hz:.1f} Hz (90% of target)"
        else:
            status['rate'] = f"WARNING: {metrics.average_hz:.1f} Hz < {self.target_hz} Hz target"

        # Data drops check
        if metrics.data_drops == 0:
            status['drops'] = "EXCELLENT: No data drops"
        elif metrics.data_drops < metrics.samples_total * 0.001:
            status['drops'] = f"GOOD: {metrics.data_drops} drops (<0.1%)"
        else:
            drop_rate = metrics.data_drops / metrics.samples_total * 100
            status['drops'] = f"WARNING: {metrics.data_drops} drops ({drop_rate:.2f}%)"

        # Memory check
        if metrics.memory_mb < 50:
            status['memory'] = f"OPTIMAL: {metrics.memory_mb:.1f} MB memory usage"
        elif metrics.memory_mb < 100:
            status['memory'] = f"GOOD: {metrics.memory_mb:.1f} MB memory usage"
        else:
            status['memory'] = f"HIGH: {metrics.memory_mb:.1f} MB memory usage"

        return status

    def print_summary(self) -> None:
        """Print performance summary"""
        metrics = self.get_metrics()
        status = self.check_performance()

        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)

        print(f"\nData Collection:")
        print(f"  Duration: {metrics.uptime_seconds:.1f} seconds")
        print(f"  Total samples: {metrics.samples_total:,}")
        print(f"  Data drops: {metrics.data_drops}")

        print(f"\nData Rates:")
        print(f"  Current: {metrics.current_hz:.1f} Hz")
        print(f"  Average: {metrics.average_hz:.1f} Hz")
        print(f"  Peak: {metrics.peak_hz:.1f} Hz")
        print(f"  Minimum: {metrics.min_hz:.1f} Hz")

        print(f"\nSystem Resources:")
        print(f"  Memory: {metrics.memory_mb:.1f} MB")
        print(f"  CPU: {metrics.cpu_percent:.1f}%")

        print(f"\nStatus:")
        for key, message in status.items():
            print(f"  {message}")

    def format_live_status(self) -> str:
        """Format live status line for display

        Returns:
            Formatted status string
        """
        metrics = self.get_metrics()

        # Color codes for terminal (optional)
        if metrics.average_hz >= self.target_hz:
            rate_status = "OK"
        elif metrics.average_hz >= self.target_hz * 0.95:
            rate_status = "GOOD"
        else:
            rate_status = "LOW"

        return (f"[{metrics.uptime_seconds:6.1f}s] "
                f"Rate: {metrics.current_hz:6.1f} Hz (avg: {metrics.average_hz:6.1f}) | "
                f"Samples: {metrics.samples_total:6d} | "
                f"Mem: {metrics.memory_mb:5.1f} MB | "
                f"GPS: {metrics.gps_status} ({metrics.satellite_count} sats) | "
                f"Status: {rate_status}")