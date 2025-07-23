"""
Bomb Timer Service for CS2 bomb countdown and defuse kit alerts.
"""
import logging
import time
from typing import Optional, Callable
from PySide6.QtCore import QTimer, QObject, Signal
from core.models.player_state import PlayerState


class BombTimerService(QObject):
    """Service for tracking bomb timer and defuse kit alerts using Qt signals."""

    # Qt signals for thread-safe communication
    bomb_planted_signal = Signal()
    bomb_defused_signal = Signal()
    timer_update_signal = Signal(float, bool, bool)  # remaining_time, has_kit, can_defuse

    def __init__(self, config_service=None):
        super().__init__()
        self.logger = logging.getLogger("BombTimerService")
        self.config_service = config_service

        self.bomb_planted_time: Optional[float] = None
        self.bomb_timer_active = False
        self.bomb_defused = False
        self.bomb_exploded = False

        self.BOMB_TIMER_DURATION = 40.0
        self.DEFUSE_TIME_WITH_KIT = 5.0
        self.DEFUSE_TIME_WITHOUT_KIT = 10.0

        self.has_defuse_kit = False
        self.current_player_state: Optional[PlayerState] = None

        self.timer_update_callback: Optional[Callable[[float, bool, bool], None]] = None
        self.defuse_alert_callback: Optional[Callable[[bool], None]] = None

        self.qt_timer = QTimer(self)
        self.qt_timer.timeout.connect(self._timer_update)

        self.bomb_planted_signal.connect(self._start_bomb_timer)
        self.bomb_defused_signal.connect(self._stop_bomb_timer)
        self.timer_update_signal.connect(self._emit_callback)

        self.logger.info("Bomb timer service initialized")

    def is_enabled(self) -> bool:
        """Check if bomb timer feature is enabled in config."""
        if not self.config_service:
            return True  # Default to enabled if no config service

        features = self.config_service.config.get("features", {})
        enabled = features.get("bomb_timer_enabled", True)

        # If feature was disabled while timer was active, stop it
        if not enabled and self.bomb_timer_active:
            self._stop_bomb_timer(defused=True)

        return enabled

    def process_player_state(self, player_state: PlayerState) -> None:
        """Process player state updates from GSI - can be called from any thread."""
        try:
            if not self.is_enabled():
                return

            self.current_player_state = player_state
            self.has_defuse_kit = player_state.has_defuse_kit

            if player_state.bomb_planted and not self.bomb_timer_active:
                self.bomb_planted_signal.emit()
            elif not player_state.bomb_planted and self.bomb_timer_active:
                self.bomb_defused_signal.emit()

        except Exception as e:
            self.logger.error("Error processing player state: %s", e)

    def _start_bomb_timer(self) -> None:
        """Start the bomb countdown timer - called in main thread via signal."""
        if self.bomb_timer_active:
            return

        self.bomb_planted_time = time.time()
        self.bomb_timer_active = True
        self.bomb_defused = False
        self.bomb_exploded = False

        # Start Qt timer (50ms intervals for smooth animation)
        self.qt_timer.start(50)

        self.logger.info("Bomb timer started")

    def _stop_bomb_timer(self, defused: bool = True) -> None:
        """Stop the bomb countdown timer - called in main thread via signal."""
        if not self.bomb_timer_active:
            return

        self.qt_timer.stop()
        self.bomb_timer_active = False
        self.bomb_defused = defused
        self.bomb_exploded = not defused

        # Final callback update
        self.timer_update_signal.emit(0.0, self.has_defuse_kit, False)

        status = "defused" if defused else "exploded"
        self.logger.info(f"Bomb timer {status}")

    def _timer_update(self) -> None:
        """Qt Timer update - called every 50ms in main thread."""
        try:
            if not self.bomb_timer_active or self.bomb_planted_time is None:
                return

            current_time = time.time()
            elapsed_time = current_time - self.bomb_planted_time
            remaining_time = max(0.0, self.BOMB_TIMER_DURATION - elapsed_time)

            # Check if bomb should explode
            if remaining_time <= 0.0:
                self._stop_bomb_timer(defused=False)
                return

            # Check defuse possibility
            defuse_time_needed = (self.DEFUSE_TIME_WITH_KIT if self.has_defuse_kit
                                else self.DEFUSE_TIME_WITHOUT_KIT)
            can_defuse = remaining_time >= defuse_time_needed

            # Emit signal for callback (thread-safe)
            self.timer_update_signal.emit(remaining_time, self.has_defuse_kit, can_defuse)

        except Exception as e:
            self.logger.error("Qt Timer update error: %s", e)

    def _emit_callback(self, remaining_time: float, has_kit: bool, can_defuse: bool) -> None:
        """Emit callback - called in main thread via signal."""
        if self.timer_update_callback:
            self.timer_update_callback(remaining_time, has_kit, can_defuse)

    def get_remaining_time(self) -> float:
        """Get current remaining bomb time in seconds."""
        if not self.bomb_timer_active or self.bomb_planted_time is None:
            return 0.0

        current_time = time.time()
        elapsed_time = current_time - self.bomb_planted_time
        return max(0.0, self.BOMB_TIMER_DURATION - elapsed_time)

    def can_defuse(self) -> bool:
        """Check if player can defuse the bomb in time."""
        if not self.bomb_timer_active:
            return False

        remaining_time = self.get_remaining_time()
        defuse_time_needed = (self.DEFUSE_TIME_WITH_KIT if self.has_defuse_kit
                            else self.DEFUSE_TIME_WITHOUT_KIT)

        return remaining_time >= defuse_time_needed

    def get_defuse_time_needed(self) -> float:
        """Get time needed to defuse based on kit availability."""
        return (self.DEFUSE_TIME_WITH_KIT if self.has_defuse_kit
                else self.DEFUSE_TIME_WITHOUT_KIT)

    def set_timer_update_callback(self, callback: Callable[[float, bool, bool], None]) -> None:
        """Set callback for timer updates. Args: (remaining_time, has_kit, can_defuse)"""
        self.timer_update_callback = callback
        self.logger.debug("Timer update callback registered")

    def set_defuse_alert_callback(self, callback: Callable[[bool], None]) -> None:
        """Set callback for defuse alerts. Args: (can_defuse)"""
        self.defuse_alert_callback = callback

    def is_active(self) -> bool:
        """Check if bomb timer is currently active."""
        return self.bomb_timer_active

    def stop(self) -> None:
        """Stop the bomb timer service."""
        if self.bomb_timer_active:
            self._stop_bomb_timer()
        self.qt_timer.stop()
        self.logger.debug("Bomb timer service stopped")

    def check_config_and_update(self) -> None:
        """Force check configuration and update state accordingly."""
        self.is_enabled()  # This will stop timer if disabled
