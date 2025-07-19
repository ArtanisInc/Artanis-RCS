"""
Weapon State Service - Centralized weapon state management.

This service eliminates the need for blockSignals by providing a single source of truth
for weapon state and tracking update sources to prevent signal loops.
"""
import logging
import threading
from typing import Optional, Callable, Set
from PyQt5.QtCore import QObject, pyqtSignal


class WeaponStateService(QObject):
    """Centralized weapon state management with source tracking."""

    # Signals
    weapon_changed = pyqtSignal(str, str)  # weapon_name, source
    weapon_ui_sync_requested = pyqtSignal(str)  # weapon_name for UI sync only

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Thread safety lock for state consistency
        self._state_lock = threading.RLock()

        # State tracking (protected by _state_lock)
        self._current_weapon: Optional[str] = None
        self._is_updating_from_gsi = False
        self._is_updating_from_ui = False

        # Callback tracking for cleanup
        self._status_callbacks: Set[Callable] = set()

    @property
    def current_weapon(self) -> str:
        """Get current weapon name."""
        return self._current_weapon or ""

    @property
    def is_updating_from_gsi(self) -> bool:
        """Check if currently updating from GSI."""
        return self._is_updating_from_gsi

    @property
    def is_updating_from_ui(self) -> bool:
        """Check if currently updating from UI."""
        return self._is_updating_from_ui

    def set_weapon_from_user(self, weapon_name: str) -> bool:
        """
        Set weapon from user interaction (combo box selection).

        Args:
            weapon_name: Name of the weapon to set

        Returns:
            bool: True if weapon state changed, False if no change
        """
        weapon_name = weapon_name or ""

        if self._current_weapon == weapon_name:
            self.logger.debug(f"Weapon unchanged: {weapon_name}")
            return False

        self.logger.debug(f"User selected weapon: {weapon_name}")

        old_weapon = self._current_weapon
        self._current_weapon = weapon_name
        self._is_updating_from_ui = True

        try:
            # Emit signal for business logic (recoil service, etc.)
            self.weapon_changed.emit(weapon_name, "user")
            self.logger.debug(f"Weapon changed from user: {old_weapon} -> {weapon_name}")
            return True

        finally:
            self._is_updating_from_ui = False

    def set_weapon_from_gsi(self, weapon_name: str) -> bool:
        """
        Set weapon from GSI detection.

        Args:
            weapon_name: Name of the weapon detected by GSI

        Returns:
            bool: True if weapon state changed, False if no change
        """
        weapon_name = weapon_name or ""

        if self._current_weapon == weapon_name:
            self.logger.debug(f"GSI weapon unchanged: {weapon_name}")
            return False

        self.logger.debug(f"GSI detected weapon: {weapon_name}")

        old_weapon = self._current_weapon
        self._current_weapon = weapon_name
        self._is_updating_from_gsi = True

        try:
            # Emit signal for UI synchronization only (no business logic)
            self.weapon_ui_sync_requested.emit(weapon_name)

            # Also emit business logic signal if weapon actually changed
            self.weapon_changed.emit(weapon_name, "gsi")

            self.logger.debug(f"Weapon changed from GSI: {old_weapon} -> {weapon_name}")
            return True

        finally:
            self._is_updating_from_gsi = False

    def clear_weapon_selection(self) -> bool:
        """
        Clear weapon selection (transition to automatic mode).

        Returns:
            bool: True if weapon state changed, False if no change
        """
        if not self._current_weapon:
            return False

        self.logger.debug("Clearing weapon selection for automatic mode")

        old_weapon = self._current_weapon
        self._current_weapon = None

        # Emit signals for both UI sync and business logic
        self.weapon_ui_sync_requested.emit("")
        self.weapon_changed.emit("", "clear")

        self.logger.debug(f"Weapon selection cleared: {old_weapon} -> None")
        return True

    def sync_weapon_state(self, weapon_name: str, source: str = "sync") -> bool:
        """
        Synchronize weapon state without triggering change events.
        Used for internal state synchronization.

        Args:
            weapon_name: Name of the weapon to sync
            source: Source of the sync operation

        Returns:
            bool: True if state was updated, False if no change
        """
        weapon_name = weapon_name or ""

        if self._current_weapon == weapon_name:
            return False

        old_weapon = self._current_weapon
        self._current_weapon = weapon_name

        self.logger.debug(f"Weapon state synced ({source}): {old_weapon} -> {weapon_name}")
        return True

    def should_process_ui_change(self) -> bool:
        """
        Check if UI changes should be processed.

        Returns:
            bool: False if currently updating from GSI, True otherwise
        """
        return not self._is_updating_from_gsi

    def should_process_gsi_change(self) -> bool:
        """
        Check if GSI changes should be processed.

        Returns:
            bool: False if currently updating from UI, True otherwise
        """
        return not self._is_updating_from_ui

    def get_state_info(self) -> dict:
        """Get current state information for debugging."""
        return {
            "current_weapon": self._current_weapon,
            "updating_from_gsi": self._is_updating_from_gsi,
            "updating_from_ui": self._is_updating_from_ui
        }
