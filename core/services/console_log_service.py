"""
Console Log Monitoring Service for CS2 console.log file parsing.
"""
import logging
import re
import time
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None  # type: ignore
    FileSystemEventHandler = object  # type: ignore
    logging.warning("Watchdog not available, falling back to polling")


class ConsoleLogFileHandler(FileSystemEventHandler):  # type: ignore
    """File system event handler for console.log changes."""

    def __init__(self, monitor_service):
        self.monitor_service = monitor_service
        self.last_modification = 0
        self.debounce_delay = 0.05

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        if event.src_path == str(self.monitor_service.console_log_path):
            current_time = time.time()

            if current_time - self.last_modification > self.debounce_delay:
                self.last_modification = current_time
                self.monitor_service._process_file_changes()


class ConsoleLogMonitorService:
    """Optimized service for monitoring CS2 console.log file with file system watchers."""

    def __init__(self, config_service=None, gsi_service=None):
        self.logger = logging.getLogger("ConsoleLogMonitorService")
        self.config_service = config_service
        self.gsi_service = gsi_service

        self.console_log_path: Optional[Path] = None
        self.monitoring_active = False
        self.observer = None
        self.file_handler: Optional[ConsoleLogFileHandler] = None
        self.monitoring_thread: Optional[threading.Thread] = None
        self.last_position = 0

        self.callbacks: Dict[str, Callable] = {}

        self.match_found_pattern = re.compile(r"Server confirmed all players", re.IGNORECASE)
        self.ping_pattern = re.compile(r"latency (\d+) msec", re.IGNORECASE)
        self.match_id_pattern = re.compile(r'\[A:1:(\d+):\d+\]')
        self.timestamp_pattern = re.compile(r'(\d{2}/\d{2} \d{2}:\d{2}:\d{2})')

        self.last_match_time = 0
        self.match_cooldown = 10
        self.processed_matches = set()
        self.max_processed_matches = 20

        self.last_file_check = 0
        self.file_check_interval = 1.0
        self.processing_lock = threading.Lock()

        self.events_processed = 0
        self.matches_detected = 0
        self.ping_updates = 0

        self._find_cs2_console_log()

        if WATCHDOG_AVAILABLE:
            self.logger.info("Console Log Monitor initialized with file system watchers")
        else:
            self.logger.info("Console Log Monitor initialized with optimized polling")

    def _find_cs2_console_log(self) -> bool:
        """Find CS2 console.log file path using GSI service paths."""
        self.logger.debug(f"Looking for console.log - GSI service available: {self.gsi_service is not None}")
        try:
            if self.gsi_service and hasattr(self.gsi_service, 'config_service'):
                gsi_config_service = self.gsi_service.config_service
                steam_paths = gsi_config_service._get_steam_paths()

                for steam_path in steam_paths:
                    if not steam_path.exists():
                        continue

                    console_log_path = steam_path / "steamapps/common/Counter-Strike Global Offensive/game/csgo/console.log"

                    if console_log_path.exists():
                        self.console_log_path = console_log_path
                        self.logger.debug(f"Found CS2 console.log via GSI service: {console_log_path}")
                        return True

        except Exception as e:
            self.logger.error(f"Error finding CS2 console.log: {e}")
        return False

    def start_monitoring(self) -> bool:
        """Start optimized console log monitoring."""
        if self.monitoring_active:
            self.logger.warning("Console log monitoring already active")
            return True

        if not self.console_log_path or not self.console_log_path.exists():
            self.logger.error("Console log path not found or invalid")
            return False

        try:
            self.last_position = self.console_log_path.stat().st_size

            if WATCHDOG_AVAILABLE and Observer is not None:
                self.observer = Observer()
                self.file_handler = ConsoleLogFileHandler(self)

                watch_dir = self.console_log_path.parent
                self.observer.schedule(self.file_handler, str(watch_dir), recursive=False)

                self.observer.start()
                self.logger.debug("Console log monitoring started with file system watchers")
            else:
                self.monitoring_thread = threading.Thread(
                    target=self._monitor_loop_optimized,
                    daemon=True,
                    name="ConsoleLogMonitor"
                )
                self.monitoring_thread.start()
                self.logger.debug("Console log monitoring started with optimized polling")

            self.monitoring_active = True
            return True

        except Exception as e:
            self.logger.error(f"Failed to start console log monitoring: {e}")
            return False

    def stop_monitoring(self) -> bool:
        """Stop console log monitoring."""
        if not self.monitoring_active:
            return True

        try:
            self.monitoring_active = False

            if WATCHDOG_AVAILABLE and self.observer:
                self.observer.stop()
                self.observer.join(timeout=2.0)
                self.observer = None

            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2.0)

            self.file_handler = None

            self.logger.debug("Console log monitoring stopped")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping console log monitoring: {e}")
            return False

    def _monitor_loop_optimized(self):
        """Polling loop as fallback when watchdog is unavailable."""
        self.logger.debug("Console log monitoring loop started (optimized polling)")
        last_size = self.last_position

        while self.monitoring_active:
            try:
                current_time = time.time()
                if current_time - self.last_file_check > self.file_check_interval:
                    self.last_file_check = current_time
                    if self.console_log_path is None or not self.console_log_path.exists():
                        self.logger.warning("Console log file no longer exists")
                        break

                assert self.console_log_path is not None  # Type guard for mypy/pylance
                current_size = self.console_log_path.stat().st_size

                if current_size != last_size:
                    self._process_file_changes()
                    last_size = current_size

            except Exception as e:
                self.logger.error(f"Error in console log monitoring loop: {e}")

            time.sleep(0.2)

        self.logger.debug("Console log monitoring loop ended")

    def _process_file_changes(self):
        """Process file changes detected by file system watcher or polling."""
        if not self.monitoring_active:
            return

        if not self.processing_lock.acquire(blocking=False):
            return

        try:
            if not self.console_log_path or not self.console_log_path.exists():
                return

            current_size = self.console_log_path.stat().st_size

            if current_size > self.last_position:
                with open(str(self.console_log_path), 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(self.last_position)
                    new_content = f.read()

                if new_content:
                    self._process_new_content(new_content)

                self.last_position = current_size

            elif current_size < self.last_position:
                self.logger.debug("Console log file was truncated, resetting position")
                self.last_position = 0

        except Exception as e:
            self.logger.error(f"Error processing file changes: {e}")
        finally:
            self.processing_lock.release()

    def _process_new_content(self, content: str):
        """Process new console log content with optimized pattern matching."""
        try:
            lines = content.split('\n')
            self.events_processed += len(lines)

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if self.match_found_pattern.search(line):
                    if self._handle_match_found(line):
                        self.matches_detected += 1

                elif self.ping_pattern.search(line):
                    ping_match = self.ping_pattern.search(line)
                    if ping_match:
                        ping_value = int(ping_match.group(1))
                        self.ping_updates += 1
                        self._trigger_callback('ping_update', ping_value)

                if 'new_line' in self.callbacks:
                    self._trigger_callback('new_line', line)

        except Exception as e:
            self.logger.error(f"Error processing console log content: {e}")

    def _handle_match_found(self, line: str) -> bool:
        """Handle match found event with optimized duplicate detection."""
        try:
            match_id = self._extract_match_id_optimized(line)
            current_time = time.time()

            if (current_time - self.last_match_time > self.match_cooldown and
                match_id not in self.processed_matches):

                self.logger.info("Match found detected in console log")
                self.last_match_time = current_time
                self.processed_matches.add(match_id)

                if len(self.processed_matches) > self.max_processed_matches:
                    sorted_matches = sorted(self.processed_matches)
                    keep_count = self.max_processed_matches // 2
                    self.processed_matches = set(sorted_matches[-keep_count:])

                self._trigger_callback('match_found', line)
                return True
            else:
                self.logger.debug(f"Duplicate match detection ignored: {match_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error handling match found: {e}")
            return False

    def _extract_match_id_optimized(self, line: str) -> str:
        """Extract unique match identifier from console line."""
        try:
            match_id_match = self.match_id_pattern.search(line)
            if match_id_match:
                return match_id_match.group(1)

            timestamp_match = self.timestamp_pattern.search(line)
            if timestamp_match:
                return timestamp_match.group(1)

            import hashlib
            return hashlib.md5(line[:50].encode()).hexdigest()[:8]

        except Exception as e:
            self.logger.error(f"Error extracting match ID: {e}")
            return str(int(time.time()))

    def _trigger_callback(self, event_type: str, data):
        """Trigger registered callback for event type."""
        if event_type in self.callbacks:
            try:
                self.callbacks[event_type](data)
            except Exception as e:
                self.logger.error(f"Error in callback for {event_type}: {e}")

    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for specific event type."""
        self.callbacks[event_type] = callback
        self.logger.debug(f"Callback registered for event: {event_type}")

    def unregister_callback(self, event_type: str):
        """Unregister callback for specific event type."""
        if event_type in self.callbacks:
            del self.callbacks[event_type]
            self.logger.debug(f"Callback unregistered for event: {event_type}")
