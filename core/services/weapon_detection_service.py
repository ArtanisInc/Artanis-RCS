"""
Weapon detection service for automatic RCS control.
"""
import logging
import threading
import time
from typing import Optional, Dict, Any

from core.models.player_state import PlayerState, WeaponState
from core.services.recoil_service import RecoilService


class WeaponDetectionState:
    """Tracks weapon detection state with thread safety."""

    def __init__(self):
        self._lock = threading.Lock()
        self.current_weapon: Optional[str] = None
        self.previous_weapon: Optional[str] = None
        self.rcs_was_auto_enabled: bool = False
        self.last_ammo_count: int = -1
        self.last_update_time: float = 0.0
        self.weapon_change_count: int = 0

    def update_weapon(self, weapon_name: Optional[str]) -> bool:
        """Update current weapon and detect changes (thread-safe)."""
        with self._lock:
            if weapon_name != self.current_weapon:
                self.previous_weapon = self.current_weapon
                self.current_weapon = weapon_name
                self.weapon_change_count += 1
                return True
            return False

    def update_ammo(self, ammo_count: int) -> bool:
        """Update ammo count and detect state changes (thread-safe)."""
        with self._lock:
            current_is_empty = ammo_count == 0
            previous_was_empty = self.last_ammo_count == 0

            if (self.last_ammo_count >= 0 and
                    current_is_empty != previous_was_empty):
                self.last_ammo_count = ammo_count
                return True

            self.last_ammo_count = ammo_count
            return False

    def reset(self):
        """Reset detection state (thread-safe)."""
        with self._lock:
            self.current_weapon = None
            self.previous_weapon = None
            self.rcs_was_auto_enabled = False
            self.last_ammo_count = -1


class WeaponDetectionService:
    """Automatic weapon detection and RCS control service."""

    def __init__(self, recoil_service: RecoilService):
        self.logger = logging.getLogger("WeaponDetectionService")
        self.recoil_service = recoil_service

        self.enabled = False
        self.detection_state = WeaponDetectionState()
        self.startup_time = time.time()

        self.low_ammo_threshold = 5

        self.logger.debug("Weapon detection service initialized")

    def enable(self) -> bool:
        """Enable automatic weapon detection."""
        if self.enabled:
            return True

        try:
            self.enabled = True
            self.detection_state.reset()

            # This ensures clean state until GSI provides weapon data
            if self.recoil_service.current_weapon:
                self.logger.debug("Clearing manually set weapon: %s",
                                self.recoil_service.current_weapon)
                self.recoil_service.current_weapon = None

            # Always notify status change when detection state changes
            self.recoil_service.notify_status_changed()

            self.logger.info("Weapon detection enabled")

            return True

        except Exception as e:
            self.logger.error("Failed to enable weapon detection: %s", e)
            return False

    def disable(self) -> bool:
        """Disable automatic weapon detection."""
        if not self.enabled:
            return True

        try:
            self.enabled = False

            if (self.detection_state.rcs_was_auto_enabled and
                    self.recoil_service.active):
                self.recoil_service.stop_compensation()
                self.detection_state.rcs_was_auto_enabled = False

            self.detection_state.reset()

            # Notify RecoilService to update UI status when detection is disabled
            self.recoil_service.notify_status_changed()

            self.logger.info("Weapon detection disabled")

            return True

        except Exception as e:
            self.logger.error("Failed to disable weapon detection: %s", e)
            return False

    def toggle_detection(self) -> bool:
        """Toggle weapon detection state."""
        if self.enabled:
            return self.disable()
        else:
            return self.enable()

    def process_player_state(self, player_state: PlayerState) -> None:
        """Process player state and update RCS accordingly."""
        if not self.enabled:
            return

        try:
            current_time = time.time()

            self.detection_state.last_update_time = current_time

            self._process_weapon_changes(player_state)
            self._process_rcs_control(player_state, current_time)
            self._process_ammo_monitoring(player_state)

        except Exception as e:
            self.logger.error("Player state processing error: %s", e)

    def _process_weapon_changes(self, player_state: PlayerState) -> None:
        """Process weapon changes and update active weapon."""
        target_weapon = None

        if player_state.should_enable_rcs:
            pattern_name = player_state.rcs_weapon_pattern
            if pattern_name:
                target_weapon = pattern_name

        weapon_changed = self.detection_state.update_weapon(target_weapon)

        if weapon_changed:
            self._handle_weapon_change(target_weapon)

    def _handle_weapon_change(self, new_weapon: Optional[str]) -> None:
        """Handle weapon change event with silent operation."""
        try:
            if new_weapon:
                success = self.recoil_service.set_weapon(new_weapon)
                if success:
                    # Only log weapon switches, not reconfirmations
                    if new_weapon != self.detection_state.previous_weapon:
                        self.logger.debug("Auto-switched to weapon: %s", new_weapon)
                    else:
                        self.logger.debug("Weapon reconfirmed: %s", new_weapon)
                else:
                    self.logger.warning("Failed to switch to: %s (weapon not in profiles)", new_weapon)
            else:
                # Clear weapon when no valid weapon detected
                self.recoil_service.set_weapon(None)
                self.logger.debug("No valid RCS weapon detected - cleared weapon")

        except Exception as e:
            self.logger.error("Weapon change handling error: %s", e)

    def _process_rcs_control(self, player_state: PlayerState,
                             current_time: float) -> None:
        """Process automatic RCS enable/disable control."""

        should_enable_rcs = player_state.should_enable_rcs
        rcs_currently_active = self.recoil_service.active

        try:
            if should_enable_rcs and not rcs_currently_active:
                if self.recoil_service.current_weapon:
                    success = self.recoil_service.start_compensation(
                        allow_manual_when_auto_enabled=True)
                    if success:
                        self.detection_state.rcs_was_auto_enabled = True
                        self.logger.debug("RCS auto-enabled by GSI detection")
                else:
                    self.logger.debug("Cannot start RCS: no weapon set in recoil service")

            elif (not should_enable_rcs and rcs_currently_active and
                  self.detection_state.rcs_was_auto_enabled):
                success = self.recoil_service.stop_compensation()
                if success:
                    self.detection_state.rcs_was_auto_enabled = False
                    self.logger.debug("RCS auto-disabled")

        except Exception as e:
            self.logger.error("RCS control error: %s", e)


    def _process_ammo_monitoring(self, player_state: PlayerState) -> None:
        """Process ammunition monitoring with silent operation."""
        if not player_state.active_weapon:
            return

        weapon = player_state.active_weapon
        ammo_state_changed = self.detection_state.update_ammo(weapon.ammo_clip)

        if (weapon.ammo_clip <= self.low_ammo_threshold and
            weapon.ammo_clip > 0 and
            ammo_state_changed and
                weapon.is_rcs_eligible):

            self._handle_low_ammo_warning(weapon)

        if weapon.ammo_clip == 0 and ammo_state_changed:
            self._handle_empty_magazine(weapon)

    def _handle_low_ammo_warning(self, weapon: WeaponState) -> None:
        """Handle low ammunition warning silently."""
        try:
            self.logger.debug(
                "Low ammo detected: %s (%s)",
                weapon.name, weapon.ammo_clip)
            # No TTS announcement to avoid interrupting gameplay

        except Exception as e:
            self.logger.error("Low ammo warning error: %s", e)

    def _handle_empty_magazine(self, weapon: WeaponState) -> None:
        """Handle empty magazine detection silently."""
        try:
            self.logger.debug("Empty magazine detected: %s", weapon.name)
            # No TTS announcement to avoid interrupting gameplay

        except Exception as e:
            self.logger.error("Empty magazine handling error: %s", e)

    def configure(self, config: Dict[str, Any]) -> bool:
        """Update detection configuration."""
        try:
            self.low_ammo_threshold = config.get("low_ammo_threshold",
                                                 self.low_ammo_threshold)

            self.logger.debug("Configuration updated")
            return True

        except Exception as e:
            self.logger.error("Configuration update failed: %s", e)
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get status information"""
        return {
            "enabled": self.enabled,
            "current_state": {
                "weapon": self.detection_state.current_weapon
            }
        }
