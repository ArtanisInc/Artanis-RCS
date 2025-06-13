"""
Weapon detection service for automatic RCS control.
"""
import logging
import time
from typing import Optional, Dict, Any

from core.models.player_state import PlayerState, WeaponState
from core.services.recoil_service import RecoilService


class WeaponDetectionState:
    """Tracks weapon detection state."""

    def __init__(self):
        self.current_weapon: Optional[str] = None
        self.previous_weapon: Optional[str] = None
        self.rcs_was_auto_enabled: bool = False
        self.last_ammo_count: int = -1
        self.last_update_time: float = 0.0
        self.weapon_change_count: int = 0

    def update_weapon(self, weapon_name: Optional[str]) -> bool:
        """Update current weapon and detect changes."""
        if weapon_name != self.current_weapon:
            self.previous_weapon = self.current_weapon
            self.current_weapon = weapon_name
            self.weapon_change_count += 1
            return True
        return False

    def update_ammo(self, ammo_count: int) -> bool:
        """Update ammo count and detect state changes."""
        current_is_empty = ammo_count == 0
        previous_was_empty = self.last_ammo_count == 0

        if (self.last_ammo_count >= 0 and
                current_is_empty != previous_was_empty):
            self.last_ammo_count = ammo_count
            return True

        self.last_ammo_count = ammo_count
        return False

    def reset(self):
        """Reset detection state."""
        self.current_weapon = None
        self.previous_weapon = None
        self.rcs_was_auto_enabled = False
        self.last_ammo_count = -1


class WeaponDetectionService:
    """Automatic weapon detection and RCS control service."""

    # Startup protection timing
    STARTUP_GRACE_PERIOD = 3.0

    def __init__(self, recoil_service: RecoilService):
        self.logger = logging.getLogger("WeaponDetectionService")
        self.recoil_service = recoil_service

        self.enabled = False
        self.detection_state = WeaponDetectionState()
        self.startup_time = time.time()
        self.user_initiated_start = False

        self.auto_weapon_switch = True
        self.auto_rcs_control = True
        self.low_ammo_threshold = 5
        self.min_transition_delay = 0.2
        self.announce_weapon_changes = False  # Disable TTS for auto changes

        self.statistics = {
            "total_updates": 0,
            "weapon_switches": 0,
            "rcs_activations": 0,
            "rcs_deactivations": 0,
            "ammo_warnings": 0,
            "last_activity": 0.0
        }

        self.logger.debug("Weapon detection service initialized")

    def enable(self) -> bool:
        """Enable automatic weapon detection."""
        if self.enabled:
            return True

        try:
            self.enabled = True
            self.detection_state.reset()
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
            self.logger.info("Weapon detection disabled")

            return True

        except Exception as e:
            self.logger.error("Failed to disable weapon detection: %s", e)
            return False

    def set_user_initiated_start(self, initiated: bool = True):
        """Mark that user has manually initiated RCS at least once."""
        self.user_initiated_start = initiated
        if initiated:
            self.logger.debug("User-initiated RCS start recorded")

    def process_player_state(self, player_state: PlayerState) -> None:
        """Process player state and update RCS accordingly."""
        if not self.enabled:
            return

        try:
            current_time = time.time()

            if (current_time - self.detection_state.last_update_time <
                    self.min_transition_delay):
                return

            self.detection_state.last_update_time = current_time
            self.statistics["total_updates"] += 1
            self.statistics["last_activity"] = current_time

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

        if weapon_changed and self.auto_weapon_switch:
            self._handle_weapon_change(target_weapon,
                                       player_state.active_weapon)

    def _handle_weapon_change(self, new_weapon: Optional[str],
                              weapon_state: Optional[WeaponState]) -> None:
        """Handle weapon change event with silent operation."""
        try:
            self.statistics["weapon_switches"] += 1

            if new_weapon:
                success = self.recoil_service.set_weapon(new_weapon)
                if success:
                    self.logger.info("Auto-switched to weapon: %s", new_weapon)

                    # Silent weapon change - no TTS announcement
                    # The TTS suppression is handled by
                    # RecoilService._should_announce_weapon()
                    self.logger.debug(
                        "Weapon change completed silently via GSI detection")
                else:
                    self.logger.warning("Failed to switch to: %s", new_weapon)
            else:
                self.logger.debug("No valid RCS weapon detected")

        except Exception as e:
            self.logger.error("Weapon change handling error: %s", e)

    def _process_rcs_control(self, player_state: PlayerState,
                             current_time: float) -> None:
        """Process automatic RCS enable/disable control with startup protection."""
        if not self.auto_rcs_control:
            return

        # Protection against automatic startup activation
        if not self._should_allow_auto_activation(current_time):
            return

        should_enable_rcs = player_state.should_enable_rcs
        rcs_currently_active = self.recoil_service.active

        try:
            if should_enable_rcs and not rcs_currently_active:
                if self.detection_state.current_weapon:
                    success = self.recoil_service.start_compensation(
                        allow_manual_when_auto_enabled=True)
                    if success:
                        self.detection_state.rcs_was_auto_enabled = True
                        self.statistics["rcs_activations"] += 1
                        self.logger.info("RCS auto-enabled by GSI detection")

            elif (not should_enable_rcs and rcs_currently_active and
                  self.detection_state.rcs_was_auto_enabled):
                success = self.recoil_service.stop_compensation()
                if success:
                    self.detection_state.rcs_was_auto_enabled = False
                    self.statistics["rcs_deactivations"] += 1
                    self.logger.debug("RCS auto-disabled")

        except Exception as e:
            self.logger.error("RCS control error: %s", e)

    def _should_allow_auto_activation(self, current_time: float) -> bool:
        """Determine if automatic RCS activation should be allowed."""
        # Grace period after startup
        if current_time - self.startup_time < self.STARTUP_GRACE_PERIOD:
            self.logger.debug("Auto-activation blocked: startup grace period")
            return False

        # Allow only if user has already started manually
        # or if sufficient time has elapsed
        grace_period_elapsed = (current_time - self.startup_time >
                                self.STARTUP_GRACE_PERIOD * 2)

        if not self.user_initiated_start and not grace_period_elapsed:
            self.logger.debug(
                "Auto-activation blocked: waiting for user initiation")
            return False

        return True

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
            self.statistics["ammo_warnings"] += 1
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
            self.auto_weapon_switch = config.get("auto_weapon_switch",
                                                 self.auto_weapon_switch)
            self.auto_rcs_control = config.get("auto_rcs_control",
                                               self.auto_rcs_control)
            self.low_ammo_threshold = config.get("low_ammo_threshold",
                                                 self.low_ammo_threshold)
            self.min_transition_delay = config.get("transition_delay",
                                                   self.min_transition_delay)
            self.announce_weapon_changes = config.get(
                "announce_weapon_changes", self.announce_weapon_changes)

            self.logger.debug("Configuration updated")
            return True

        except Exception as e:
            self.logger.error("Configuration update failed: %s", e)
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information."""
        current_time = time.time()

        return {
            "enabled": self.enabled,
            "current_state": {
                "weapon": self.detection_state.current_weapon,
                "previous_weapon": self.detection_state.previous_weapon,
                "rcs_auto_enabled": self.detection_state.rcs_was_auto_enabled,
                "last_ammo": self.detection_state.last_ammo_count,
                "weapon_changes": self.detection_state.weapon_change_count,
                "user_initiated": self.user_initiated_start
            },
            "configuration": {
                "auto_weapon_switch": self.auto_weapon_switch,
                "auto_rcs_control": self.auto_rcs_control,
                "low_ammo_threshold": self.low_ammo_threshold,
                "min_transition_delay": self.min_transition_delay,
                "announce_weapon_changes": self.announce_weapon_changes
            },
            "timing": {
                "startup_time": self.startup_time,
                "grace_period_remaining": max(0, self.STARTUP_GRACE_PERIOD -
                                              (current_time - self.startup_time)),
                "auto_activation_allowed": self._should_allow_auto_activation(current_time)
            },
            "statistics": self.statistics.copy(),
            "recoil_service": {
                "active": self.recoil_service.active,
                "current_weapon": self.recoil_service.current_weapon
            }
        }
