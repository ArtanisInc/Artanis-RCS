"""
Auto Accept Service for automatically accepting CS2 matches.
"""
import logging
import time
import threading
from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal
import win32api
import win32con
import win32gui

from core.services.console_log_service import ConsoleLogMonitorService
from core.services.screen_capture_service import ScreenCaptureService


class AutoAcceptService(QObject):
    """Service for automatically accepting CS2 matches when found."""

    # Qt signals for thread-safe communication
    match_found_signal = Signal()
    match_accepted_signal = Signal()
    status_update_signal = Signal(str)  # Status message

    def __init__(self, config_service, input_service, tts_service=None):
        super().__init__()
        self.logger = logging.getLogger("AutoAcceptService")
        self.config_service = config_service
        self.input_service = input_service
        self.tts_service = tts_service

        self.console_monitor = ConsoleLogMonitorService(config_service)
        self.screen_capture = ScreenCaptureService()

        self.gsi_service = None

        self.enabled = False
        self.accepting_in_progress = False
        self.accept_thread: Optional[threading.Thread] = None

        self.waiting_time = 5  # Default waiting time in seconds
        self.target_color = (54, 183, 82)  # Green Accept button color
        self.color_tolerance = 20

        self.match_found_signal.connect(self._on_match_found_signal)

        # Register console log callback
        self.console_monitor.register_callback('match_found', self._on_match_found_in_console)

        self.logger.info("Auto Accept Service initialized")

    def should_be_enabled(self) -> bool:
        """Check if Auto Accept should be enabled based on features configuration."""
        try:
            if not self.config_service:
                return False

            features = self.config_service.config.get("features", {})
            return features.get("auto_accept_enabled", False)
        except Exception as e:
            self.logger.error(f"Error checking Auto Accept enabled state: {e}")
            return False

    def set_gsi_service(self, gsi_service):
        """Set GSI service reference and update console monitor."""
        self.gsi_service = gsi_service
        self.logger.debug(f"GSI service set: {gsi_service is not None}")
        if self.console_monitor:
            self.console_monitor.gsi_service = gsi_service
            # Re-initialize console log path detection with GSI service
            result = self.console_monitor._find_cs2_console_log()
            self.logger.debug(f"Console log detection result: {result}")
            if result:
                self.logger.debug(f"Console log path: {self.console_monitor.console_log_path}")
            else:
                self.logger.warning("Failed to find console.log after GSI service setup")

        # Auto-start if enabled in configuration
        self._check_auto_start()

    def _check_auto_start(self):
        """Check if Auto Accept should be automatically started based on configuration."""
        try:
            if self.should_be_enabled() and not self.enabled:
                self.logger.debug("Auto Accept enabled in config - starting automatically")
                self.enable()
            elif not self.should_be_enabled() and self.enabled:
                self.logger.debug("Auto Accept disabled in config - stopping automatically")
                self.disable()
        except Exception as e:
            self.logger.error(f"Error during auto-start check: {e}")

    def enable(self) -> bool:
        """Enable Auto Accept service."""
        if self.enabled:
            self.logger.debug("Auto Accept already enabled")
            return True

        try:
            # Start console log monitoring
            if not self.console_monitor.start_monitoring():
                self.logger.error("Failed to start console log monitoring")
                return False

            self.enabled = True
            self.status_update_signal.emit("Auto Accept enabled")


            self.logger.debug("Auto Accept service enabled")
            return True

        except Exception as e:
            self.logger.error(f"Error enabling Auto Accept service: {e}")
            return False

    def disable(self) -> bool:
        """Disable Auto Accept service."""
        if not self.enabled:
            return True

        try:
            self.enabled = False

            # Stop console log monitoring
            self.console_monitor.stop_monitoring()

            # Wait for any ongoing accept process to finish
            if self.accept_thread and self.accept_thread.is_alive():
                self.accept_thread.join(timeout=2.0)

            self.status_update_signal.emit("Auto Accept disabled")


            self.logger.debug("Auto Accept service disabled")
            return True

        except Exception as e:
            self.logger.error(f"Error disabling Auto Accept service: {e}")
            return False

    def _on_match_found_in_console(self, line: str):
        """Handle match found event from console log."""
        if not self.enabled:
            return

        self.logger.info(f"Match found in console: {line}")
        self.match_found_signal.emit()

    def _on_match_found_signal(self):
        """Handle match found Qt signal (thread-safe)."""
        if not self.enabled or self.accepting_in_progress:
            return

        self.accepting_in_progress = True

        # Start accept process in separate thread
        self.accept_thread = threading.Thread(
            target=self._accept_match_process,
            daemon=True,
            name="AutoAcceptProcess"
        )
        self.accept_thread.start()

    def _accept_match_process(self):
        """Main process for accepting a match."""
        try:
            self.logger.debug("Starting Auto Accept process")
            self.status_update_signal.emit("Match found! Starting Auto Accept...")

            if self.tts_service:
                self.tts_service.speak("Match found")

            # Store current mouse position
            current_pos = win32gui.GetCursorPos()

            # Get CS2 window info
            window_info = self.screen_capture.get_window_info()
            if not window_info:
                self.logger.error("CS2 window not found")
                self.status_update_signal.emit("Error: CS2 window not found")
                return

            # Ensure CS2 window is brought to foreground with verification
            if not self._ensure_window_foreground():
                self.logger.warning("Failed to bring CS2 window to foreground, but continuing...")
                self.status_update_signal.emit("Warning: CS2 may not be in foreground, but trying to accept...")
                # Don't return - continue with the process

            # Additional wait to ensure window is fully active
            time.sleep(0.3)

            # Calculate Accept button position
            button_x, button_y = self.screen_capture.calculate_accept_button_position(window_info)
            self.logger.debug("Accept button position calculated: ({}, {}) for window {}".format(button_x, button_y, window_info))

            # Monitor for Accept button and click when found
            accept_clicked = False
            start_time = time.time()

            while time.time() - start_time < self.waiting_time:
                if not self.enabled:
                    self.logger.info("Auto Accept disabled during process")
                    break

                # Check if Accept button is visible (green color)
                current_color = self.screen_capture.get_pixel_color(button_x, button_y)
                if current_color:
                    self.logger.debug(f"Pixel color at ({button_x}, {button_y}): {current_color}")

                if self.screen_capture.verify_accept_button_color(window_info, self.target_color, self.color_tolerance):
                    self.logger.info(f"Accept button detected at ({button_x}, {button_y}), clicking...")

                    # Move mouse to Accept button and click
                    self._click_at_position(button_x, button_y)

                    accept_clicked = True
                    self.match_accepted_signal.emit()
                    self.status_update_signal.emit("Match accepted successfully!")


                    self.logger.info("Match accepted successfully")
                    break

                # Small delay before next check
                time.sleep(0.1)

            # Restore mouse position
            if current_pos:
                win32api.SetCursorPos(current_pos)

            if not accept_clicked:
                self.logger.warning("Accept button not found within timeout")
                self.status_update_signal.emit("Timeout: Accept button not found")



        except Exception as e:
            self.logger.error(f"Error in Auto Accept process: {e}")
            self.status_update_signal.emit(f"Error: {e}")

        finally:
            self.accepting_in_progress = False

    def _ensure_window_foreground(self, max_attempts: int = 3) -> bool:
        """
        Ensure CS2 window is brought to foreground with verification and retry logic.

        Args:
            max_attempts: Maximum number of attempts to bring window to foreground

        Returns:
            True if window is successfully brought to foreground
        """
        try:
            # Check if CS2 is already in foreground
            if self.screen_capture.is_window_foreground():
                self.logger.debug("CS2 window is already in foreground")
                return True

            self.logger.debug("CS2 window not in foreground, attempting to bring to front")

            for attempt in range(max_attempts):
                self.logger.debug(f"Foreground attempt {attempt + 1}/{max_attempts}")

                # Attempt to bring window to foreground
                if self.screen_capture.bring_window_to_front():
                    # Wait a moment for the window to become active
                    time.sleep(0.2)

                    # Verify the window is now in foreground
                    if self.screen_capture.is_window_foreground():
                        self.logger.debug("CS2 window successfully brought to foreground")
                        return True
                    else:
                        self.logger.warning(f"Attempt {attempt + 1}: Window activation failed, retrying...")
                        # Wait a bit longer before retry
                        time.sleep(0.3)
                else:
                    self.logger.warning(f"Attempt {attempt + 1}: Failed to call bring_window_to_front")
                    time.sleep(0.3)

            self.logger.error("Failed to bring CS2 window to foreground after all attempts")
            return False

        except Exception as e:
            self.logger.error(f"Error ensuring window foreground: {e}")
            return False

    def _get_cursor_position(self) -> Optional[tuple]:
        """Get current cursor position."""
        try:
            x, y = win32gui.GetCursorPos()
            return (x, y)
        except Exception as e:
            self.logger.error(f"Error getting cursor position: {e}")
            return None

    def _move_cursor_to(self, x: int, y: int):
        """Move cursor to absolute position."""
        try:
            win32api.SetCursorPos((x, y))
        except Exception as e:
            self.logger.error(f"Error moving cursor to ({x}, {y}): {e}")

    def _click_at_position(self, x: int, y: int):
        """Click at specific position."""
        try:
            # Move cursor to position
            self._move_cursor_to(x, y)
            time.sleep(0.01)  # Small delay

            # Use win32api for mouse click - coordinates should be 0,0 for mouse_event
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)  # Hold click briefly
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

            self.logger.debug(f"Clicked at position ({x}, {y})")

        except Exception as e:
            self.logger.error(f"Error clicking at position ({x}, {y}): {e}")

    def is_enabled(self) -> bool:
        """Check if Auto Accept is enabled."""
        return self.enabled

    def is_accepting(self) -> bool:
        """Check if currently accepting a match."""
        return self.accepting_in_progress
