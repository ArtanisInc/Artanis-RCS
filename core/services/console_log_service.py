"""
Console Log Monitoring Service for CS2 console.log file parsing.
"""
import logging
import re
import time
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any


class ConsoleLogMonitorService:
    """Service for monitoring CS2 console.log file and detecting match events."""

    def __init__(self, config_service=None, gsi_service=None):
        self.logger = logging.getLogger("ConsoleLogMonitorService")
        self.config_service = config_service
        self.gsi_service = gsi_service

        # File monitoring state
        self.console_log_path: Optional[Path] = None
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.last_position = 0

        # Event callbacks
        self.callbacks: Dict[str, Callable] = {}

        # Auto Accept specific patterns
        self.match_found_pattern = re.compile(r"Server confirmed all players")
        self.ping_pattern = re.compile(r"latency (\d+) msec")

        # Duplicate detection prevention
        self.last_match_time = 0
        self.match_cooldown = 10  # seconds between match detections
        self.processed_matches = set()  # Track processed match IDs

        # Initialize paths
        self._find_cs2_console_log()

        self.logger.info("Console Log Monitor initialized")

    def _find_cs2_console_log(self) -> bool:
        """Find CS2 console.log file path using GSI service paths."""
        self.logger.debug(f"Looking for console.log - GSI service available: {self.gsi_service is not None}")
        try:
            # If GSI service is available, use its superior path detection
            if self.gsi_service and hasattr(self.gsi_service, 'config_service'):
                gsi_config_service = self.gsi_service.config_service
                steam_paths = gsi_config_service._get_steam_paths()

                for steam_path in steam_paths:
                    if not steam_path.exists():
                        continue

                    # CS2 console.log location
                    console_log_path = steam_path / "steamapps/common/Counter-Strike Global Offensive/game/csgo/console.log"

                    if console_log_path.exists():
                        self.console_log_path = console_log_path
                        self.logger.debug(f"Found CS2 console.log via GSI service: {console_log_path}")
                        return True

        except Exception as e:
            self.logger.error(f"Error finding CS2 console.log: {e}")
        return False


    def start_monitoring(self) -> bool:
        """Start console log monitoring."""
        if self.monitoring_active:
            self.logger.warning("Console log monitoring already active")
            return True

        if not self.console_log_path or not self.console_log_path.exists():
            self.logger.error("Console log path not found or invalid")
            return False

        try:
            # Get current file size to start monitoring from end
            # Ensure console_log_path is not None before calling .stat()
            if self.console_log_path:
                self.last_position = self.console_log_path.stat().st_size
            else:
                self.logger.error("console_log_path is None, cannot get file size.")
                return False

            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="ConsoleLogMonitor"
            )
            self.monitoring_thread.start()

            self.logger.debug("Console log monitoring started")
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

            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2.0)

            self.logger.debug("Console log monitoring stopped")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping console log monitoring: {e}")
            return False

    def _monitor_loop(self):
        """Main monitoring loop."""
        self.logger.debug("Console log monitoring loop started")

        while self.monitoring_active:
            try:
                if not self.console_log_path or not self.console_log_path.exists():
                    self.logger.warning("Console log file no longer exists")
                    break

                # Check if file has grown
                current_size = self.console_log_path.stat().st_size

                if current_size > self.last_position:
                    # Read new content
                    with open(str(self.console_log_path), 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_position)
                        new_content = f.read()

                    if new_content:
                        self._process_new_content(new_content)

                    self.last_position = current_size
                elif current_size < self.last_position:
                    # File was truncated/recreated
                    self.logger.debug("Console log file was truncated, resetting position")
                    self.last_position = 0

            except Exception as e:
                self.logger.error(f"Error in console log monitoring loop: {e}")

            # Small delay to prevent excessive CPU usage
            time.sleep(0.1)

        self.logger.debug("Console log monitoring loop ended")

    def _process_new_content(self, content: str):
        """Process new console log content."""
        try:
            lines = content.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check for match found pattern
                if self.match_found_pattern.search(line):
                    # Extract match ID to prevent duplicates
                    match_id = self._extract_match_id(line)
                    current_time = time.time()

                    # Check cooldown and duplicate detection
                    if (current_time - self.last_match_time > self.match_cooldown and
                        match_id not in self.processed_matches):

                        self.logger.info("Match found detected in console log")
                        self.last_match_time = current_time
                        self.processed_matches.add(match_id)

                        # Clean old match IDs (keep last 10)
                        if len(self.processed_matches) > 10:
                            self.processed_matches.clear()

                        self._trigger_callback('match_found', line)
                    else:
                        self.logger.debug(f"Duplicate match detection ignored: {match_id}")

                # Check for ping updates
                ping_match = self.ping_pattern.search(line)
                if ping_match:
                    ping_value = int(ping_match.group(1))
                    self._trigger_callback('ping_update', ping_value)

                # Trigger generic line callback
                self._trigger_callback('new_line', line)

        except Exception as e:
            self.logger.error(f"Error processing console log content: {e}")

    def _extract_match_id(self, line: str) -> str:
        """Extract unique match identifier from console line."""
        try:
            # Extract match ID from patterns
            match_id_pattern = re.search(r'\[A:1:(\d+):\d+\]', line)
            if match_id_pattern:
                return match_id_pattern.group(1)

            # Fallback: use timestamp from line
            timestamp_pattern = re.search(r'(\d{2}/\d{2} \d{2}:\d{2}:\d{2})', line)
            if timestamp_pattern:
                return timestamp_pattern.group(1)

            # Last resort: use first 50 chars of line
            return line[:50]

        except Exception as e:
            self.logger.error(f"Error extracting match ID: {e}")
            return str(time.time())  # Fallback to current time

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

    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "monitoring_active": self.monitoring_active,
            "console_log_path": str(self.console_log_path) if self.console_log_path else None,
            "console_log_exists": self.console_log_path.exists() if self.console_log_path else False,
            "last_position": self.last_position,
            "registered_callbacks": len(self.callbacks)
        }
