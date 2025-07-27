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
    """Service for monitoring CS2 console.log file with optimized performance."""

    def __init__(self, config_service=None, gsi_service=None):
        self.logger = logging.getLogger("ConsoleLogMonitorService")
        self.config_service = config_service
        self.gsi_service = gsi_service

        self.console_log_path: Optional[Path] = None
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.last_position = 0

        self.callbacks: Dict[str, Callable] = {}

        self.match_found_pattern = re.compile(r"Server confirmed all players", re.IGNORECASE)
        self.ping_pattern = re.compile(r"latency (\d+) msec", re.IGNORECASE)
        self.match_id_pattern = re.compile(r'\[A:1:(\d+):\d+\]')

        self.last_match_time = 0
        self.match_cooldown = 8
        self.processed_matches = set()
        self.max_processed_matches = 15

        self.events_processed = 0
        self.matches_detected = 0

        self._find_cs2_console_log()
        self.logger.info("Console Log Monitor initialized")

    def _find_cs2_console_log(self) -> bool:
        """Find CS2 console.log file path using GSI service paths."""
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
                        return True

        except Exception as e:
            self.logger.error(f"Error finding CS2 console.log: {e}")
        return False

    def start_monitoring(self) -> bool:
        """Start console log monitoring."""
        if self.monitoring_active:
            return True

        if not self.console_log_path or not self.console_log_path.exists():
            self.logger.error("Console log path not found")
            return False

        try:
            self.last_position = self.console_log_path.stat().st_size
            self.monitoring_active = True

            self.monitoring_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="ConsoleLogMonitor"
            )
            self.monitoring_thread.start()
            return True

        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            return False

    def stop_monitoring(self) -> bool:
        """Stop console log monitoring."""
        if not self.monitoring_active:
            return True

        try:
            self.monitoring_active = False

            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2.0)

            return True

        except Exception as e:
            self.logger.error(f"Error stopping monitoring: {e}")
            return False

    def _monitor_loop(self):
        """Optimized monitoring loop."""
        while self.monitoring_active:
            try:
                if not self.console_log_path or not self.console_log_path.exists():
                    time.sleep(0.5)
                    continue

                current_size = self.console_log_path.stat().st_size

                if current_size > self.last_position:
                    with open(str(self.console_log_path), 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_position)
                        new_content = f.read()

                    if new_content:
                        self._process_new_content(new_content)

                    self.last_position = current_size

                elif current_size < self.last_position:
                    self.last_position = 0

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(0.5)
                continue

            time.sleep(0.05)

    def _process_new_content(self, content: str):
        """Process new content with optimized pattern matching."""
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
                        self._trigger_callback('ping_update', ping_value)

                if 'new_line' in self.callbacks:
                    self._trigger_callback('new_line', line)

        except Exception as e:
            self.logger.error(f"Error processing content: {e}")

    def _handle_match_found(self, line: str) -> bool:
        """Handle match found with duplicate detection."""
        try:
            match_id = self._extract_match_id(line)
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

        except Exception as e:
            self.logger.error(f"Error handling match found: {e}")
        return False

    def _extract_match_id(self, line: str) -> str:
        """Extract match ID from console line."""
        match_id_match = self.match_id_pattern.search(line)
        if match_id_match is not None:
            return match_id_match.group(1)
        return ""

    def _trigger_callback(self, event_type: str, data):
        """Trigger registered callback."""
        if event_type in self.callbacks:
            try:
                self.callbacks[event_type](data)
            except Exception as e:
                self.logger.error(f"Error in callback for {event_type}: {e}")

    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for specific event type."""
        self.callbacks[event_type] = callback

    def unregister_callback(self, event_type: str):
        """Unregister callback for specific event type."""
        if event_type in self.callbacks:
            del self.callbacks[event_type]

    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "monitoring_active": self.monitoring_active,
            "console_log_exists": self.console_log_path.exists() if self.console_log_path else False
        }
