"""
High-precision timing service for recoil compensation.
"""
import time
import ctypes
import logging
from enum import Enum


class TimingStrategy(Enum):
    """Available timing strategies."""
    STANDARD = "standard"
    HIGH_PRECISION = "high_precision"


class WindowsTimer:
    """Windows high-precision timer using QueryPerformanceCounter."""

    def __init__(self):
        self.logger = logging.getLogger("WindowsTimer")
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.winmm = ctypes.WinDLL('winmm', use_last_error=True)

        # Initialize performance counter
        self.frequency = ctypes.c_int64()
        if not self.kernel32.QueryPerformanceFrequency(
                ctypes.byref(self.frequency)):
            raise RuntimeError("QueryPerformanceFrequency failed")
        self.freq_value = self.frequency.value

        # Set Windows timer resolution to 1ms
        self.winmm.timeBeginPeriod(1)

        # Calibrate timing overhead
        self.timing_overhead_ns = self._calibrate_timing_overhead()
        self.correction_factor = min(
            0.1, self.timing_overhead_ns / 1000000)  # Max 0.1ms

        self.logger.info(
            "Windows timer initialized (freq: %s Hz, overhead: %.0fns)",
            self.freq_value, self.timing_overhead_ns)

    def _calibrate_timing_overhead(self) -> float:
        """Calibrate timing overhead for compensation."""
        samples = 100
        overhead_measurements = []

        for _ in range(samples):
            start = self._get_raw_time()
            end = self._get_raw_time()
            overhead_measurements.append(end - start)

        # Average overhead in nanoseconds
        return (sum(overhead_measurements) /
                len(overhead_measurements)) * 1000000

    def _get_raw_time(self) -> float:
        """Get raw performance counter time."""
        counter = ctypes.c_int64()
        self.kernel32.QueryPerformanceCounter(ctypes.byref(counter))
        return counter.value / self.freq_value

    def get_time_ms(self) -> float:
        """Get current time in milliseconds."""
        return self._get_raw_time() * 1000.0

    def __del__(self):
        """Restore default timer resolution."""
        try:
            self.winmm.timeEndPeriod(1)
        except BaseException:
            pass


class PrecisionSleep:
    """High-precision sleep implementation with adaptive strategy."""

    def __init__(self, timer: WindowsTimer):
        self.timer = timer
        self.logger = logging.getLogger("PrecisionSleep")

    def sleep_absolute(
            self,
            target_time_ms: float,
            begin_time_ms: float) -> None:
        """Sleep until absolute target time from begin reference."""
        target_absolute = begin_time_ms + target_time_ms

        while True:
            current = self.timer.get_time_ms()
            remaining = target_absolute - current

            if remaining <= 0:
                break

            self._adaptive_sleep(remaining)

    def sleep_relative(self, duration_ms: float) -> None:
        """Sleep for relative duration with precision optimization."""
        if duration_ms <= 0:
            return

        # Set high resolution temporarily
        self.timer.winmm.timeBeginPeriod(1)

        try:
            start_time = self.timer.get_time_ms()
            target_time = start_time + duration_ms

            # Apply overhead correction for very short durations
            if duration_ms < 2.0:
                adjusted_target = target_time - self.timer.correction_factor
            else:
                adjusted_target = target_time

            self._execute_precision_sleep(duration_ms, adjusted_target)

        finally:
            self.timer.winmm.timeEndPeriod(1)

    def _adaptive_sleep(self, remaining_ms: float) -> None:
        """Adaptive sleep strategy based on remaining time."""
        if remaining_ms > 20.0:
            # Long duration: use OS sleep with margin
            time.sleep((remaining_ms - 15.0) / 1000.0)
        elif remaining_ms > 5.0:
            # Medium duration: short OS sleep
            time.sleep((remaining_ms - 3.0) / 1000.0)
        elif remaining_ms > 2.0:
            # Short duration: minimal sleep
            time.sleep(0.0005)  # 0.5ms
        elif remaining_ms > 0.5:
            # Very short: busy-wait
            pass
        else:
            # Sub-millisecond: tight busy-wait
            pass

    def _execute_precision_sleep(
            self,
            duration_ms: float,
            adjusted_target: float) -> None:
        """Execute precision sleep with strategy selection."""
        if duration_ms >= 10.0:
            # Long duration: hybrid approach
            time.sleep((duration_ms - 3.0) / 1000.0)
            while self.timer.get_time_ms() < adjusted_target:
                pass
        elif duration_ms >= 2.0:
            # Medium duration: minimal sleep + busy-wait
            time.sleep(0.001)  # 1ms
            while self.timer.get_time_ms() < adjusted_target:
                pass
        else:
            # Short duration: pure busy-wait with occasional yield
            while self.timer.get_time_ms() < adjusted_target:
                if (self.timer.get_time_ms() + 0.2) < adjusted_target:
                    time.sleep(0)  # Yield thread


class TimingService:
    """High-performance timing service for recoil compensation."""

    def __init__(
            self,
            strategy: TimingStrategy = TimingStrategy.HIGH_PRECISION):
        self.logger = logging.getLogger("TimingService")
        self.strategy = strategy

        try:
            self.timer = WindowsTimer()
            self.precision_sleep = PrecisionSleep(self.timer)
            self.logger.info(
                "Timing service initialized with %s strategy",
                strategy.value)
        except Exception as e:
            self.logger.error("Timing service initialization failed: %s", e)
            # Fallback to standard timing
            self.timer = None
            self.precision_sleep = None
            self.strategy = TimingStrategy.STANDARD

    def get_current_time(self) -> float:
        """Get current time in milliseconds with sub-millisecond precision."""
        if self.timer:
            return self.timer.get_time_ms()
        else:
            return time.time() * 1000.0

    def sleep(self, duration_ms: float) -> None:
        """Sleep for specified duration with high precision."""
        if duration_ms <= 0:
            return

        if self.strategy == TimingStrategy.HIGH_PRECISION and self.precision_sleep:
            self.precision_sleep.sleep_relative(duration_ms)
        else:
            # Fallback to standard sleep
            time.sleep(duration_ms / 1000.0)

    def sleep_until(self, target_time_ms: float, start_time_ms: float) -> None:
        """Sleep until target time relative to start time."""
        if self.strategy == TimingStrategy.HIGH_PRECISION and self.precision_sleep:
            self.precision_sleep.sleep_absolute(target_time_ms, start_time_ms)
        else:
            # Fallback implementation
            target_absolute = start_time_ms + target_time_ms
            current = self.get_current_time()
            remaining = target_absolute - current
            if remaining > 0:
                time.sleep(remaining / 1000.0)

    # Compatibility aliases for existing code
    def system_time(self) -> float:
        """Alias for get_current_time()."""
        return self.get_current_time()

    def combined_sleep(self, target_time: float, begin_time: float) -> None:
        """Alias for sleep_until()."""
        self.sleep_until(target_time, begin_time)

    def combined_sleep_2(self, duration: float) -> None:
        """Alias for sleep()."""
        self.sleep(duration)
