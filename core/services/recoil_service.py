"""
Recoil compensation service with TTS integration.
"""
import logging
import random
import threading
from typing import Dict, Optional, Callable, Any, List

import win32con

from core.models.weapon import WeaponProfile
from core.services.input_service import InputService
from core.services.config_service import ConfigService
from core.services.timing_service import TimingService
from core.services.tts_service import TTSService


class RecoilService:
    """Manages recoil compensation with contextual voice announcements."""

    def __init__(
            self,
            config_service: ConfigService,
            input_service: InputService,
            tts_service: Optional[TTSService] = None):
        self.logger = logging.getLogger("RecoilService")
        self.config_service = config_service
        self.input_service = input_service
        self.timing_service = TimingService()
        self.tts_service = tts_service

        self.active = False
        self.current_weapon = None
        self.running_thread = None
        self.stop_event = threading.Event()
        self.weapon_change_event = threading.Event()
        self._last_weapon_for_compensation = None

        self.weapon_detection_service = None
        self.follow_rcs_overlay = None

        self.accumulated_x = 0.0
        self.accumulated_y = 0.0

        # Raw recoil pattern position (for overlay visualization)
        self.raw_recoil_x = 0.0
        self.raw_recoil_y = 0.0

        self.status_changed_callbacks: List[Callable[[
            Dict[str, Any]], None]] = []

        self.logger.debug("Recoil service initialized")

    def set_weapon_detection_service(self, weapon_detection_service):
        """Set reference to weapon detection service for TTS coordination."""
        self.weapon_detection_service = weapon_detection_service
        self.logger.debug("Weapon detection service reference established")

    def set_follow_rcs_overlay(self, follow_rcs_overlay):
        """Set reference to follow RCS overlay for visual feedback."""
        self.follow_rcs_overlay = follow_rcs_overlay
        self.logger.debug("Follow RCS overlay reference established")

    def set_weapon(self, weapon_name: Optional[str]) -> bool:
        """Set current weapon for compensation with conditional TTS notification."""
        if not weapon_name:
            weapon_changed = self.current_weapon is not None

            if self.active:
                self.logger.debug("Stopping active compensation before weapon deselection")
                success = self.stop_compensation()
                if not success:
                    self.logger.warning("Failed to stop compensation during weapon deselection")

            self.current_weapon = None
            self.logger.info("Current weapon: None")

            if weapon_changed:
                self._notify_status_changed()

            return True

        if weapon_name not in self.config_service.weapon_profiles:
            self.logger.warning("Weapon not found: %s", weapon_name)
            return False

        weapon_changed = self.current_weapon != weapon_name
        self.current_weapon = weapon_name

        if weapon_changed:
            self.logger.info("Current weapon: %s", weapon_name)
        else:
            self.logger.debug("Weapon reconfirmed: %s", weapon_name)

        if weapon_changed and self.active:
            self.weapon_change_event.set()
            self.logger.debug(
                "Weapon change signal sent to compensation thread")

        if weapon_changed:
            self._notify_status_changed()

        return True

    def get_current_weapon(self) -> Optional[WeaponProfile]:
        """Get current weapon profile."""
        if not self.current_weapon:
            return None
        return self.config_service.get_weapon_profile(self.current_weapon)

    def start_compensation(
            self,
            key_trigger: int = win32con.VK_LBUTTON,
            allow_manual_when_auto_enabled: bool = False) -> bool:
        """Start compensation thread with conditional TTS announcement."""
        if self.active:
            self.logger.warning("Compensation already active")
            return False

        if not self.current_weapon and not self._is_manual_activation_blocked():
            self.logger.warning("No weapon selected")
            if self.tts_service:
                self.tts_service.speak("No weapon selected")
            return False

        if not allow_manual_when_auto_enabled and self._is_manual_activation_blocked():
            self.logger.info("Manual compensation start blocked: automatic weapon detection active")
            return False

        try:
            self.active = True
            self.stop_event.clear()
            self.weapon_change_event.clear()
            self._last_weapon_for_compensation = self.current_weapon

            self.running_thread = threading.Thread(
                target=self._compensation_loop,
                args=(key_trigger,),
                daemon=True
            )
            self.running_thread.start()

            if not self.weapon_detection_service or not self.weapon_detection_service.enabled:
                self.logger.info("Compensation started")
            else:
                self.logger.debug("Compensation started (auto-detection)")

            # Announce only if not in automatic weapon detection mode
            if self.tts_service and self._should_announce_weapon():
                weapon_internal_name = self.current_weapon if self.current_weapon is not None else ""
                weapon_display = self.config_service.get_weapon_display_name(
                    weapon_internal_name)
                clean_name = weapon_display.replace(
                    "-",
                    " ").replace(
                    "_",
                    " ") if weapon_display else "unknown weapon"
                self.tts_service.speak(f"Compensation active, {clean_name}")

            self._notify_status_changed()
            return True

        except Exception as e:
            self.logger.error("Compensation start failed: %s", e)
            self.active = False
            return False

    def stop_compensation(self) -> bool:
        """Stop compensation thread with conditional TTS announcement."""
        if not self.active:
            return True

        try:
            self.stop_event.set()
            if self.running_thread and self.running_thread.is_alive():
                self.running_thread.join(timeout=1.0)

            self.active = False

            if not self.weapon_detection_service or not self.weapon_detection_service.enabled:
                self.logger.info("Compensation stopped")
            else:
                self.logger.debug("Compensation stopped (auto-detection)")

            # Announce only if not in automatic weapon detection mode
            if self.tts_service and self._should_announce_weapon():
                self.tts_service.speak("Compensation stopped")

            self._notify_status_changed()
            return True

        except Exception as e:
            self.logger.error("Compensation stop failed: %s", e)
            return False

    def is_manual_activation_allowed(self) -> bool:
        """Check if manual activation is currently allowed."""
        return not self._is_manual_activation_blocked()

    def _is_manual_activation_blocked(self) -> bool:
        """Determine if manual activation should be blocked."""
        # Bloquer l'activation manuelle si la détection automatique est active
        if (self.weapon_detection_service and
                self.weapon_detection_service.enabled):
            self.logger.debug(
                "Manual activation blocked: automatic weapon detection active")
            return True

        return False

    def _should_announce_weapon(self) -> bool:
        """Determine if weapon announcements should be made."""
        # No announcements if weapon detection service is active
        if (self.weapon_detection_service and
                self.weapon_detection_service.enabled):
            self.logger.debug(
                "TTS announcement suppressed: automatic detection active")
            return False

        return True

    def register_status_changed_callback(
            self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for status changes."""
        if callback not in self.status_changed_callbacks:
            self.status_changed_callbacks.append(callback)

    def unregister_status_changed_callback(
            self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Unregister status change callback."""
        if callback in self.status_changed_callbacks:
            self.status_changed_callbacks.remove(callback)

    def _notify_status_changed(self) -> None:
        """Notify all observers of status change."""
        status = {
            'active': self.active,
            'current_weapon': self.current_weapon,
            'manual_activation_allowed': self.is_manual_activation_allowed()
        }

        for callback in self.status_changed_callbacks:
            try:
                callback(status)
            except Exception as e:
                self.logger.error("Callback notification failed: %s", e)

    def configure_tts(self, enabled: bool) -> bool:
        """Configure TTS service on-the-fly."""
        if self.tts_service:
            return self.tts_service.set_enabled(enabled)
        return False

    def _compensation_loop(self, key_trigger: int) -> None:
        """Main compensation loop."""
        self.logger.debug("Starting compensation loop")

        while not self.stop_event.is_set():
            try:
                weapon = self.get_current_weapon()
                if not weapon:
                    self.logger.error("No weapon available for compensation")
                    break

                pattern = weapon.calculated_pattern
                if not pattern:
                    self.logger.error("Empty pattern for weapon")
                    break

                if self._last_weapon_for_compensation != weapon.name:
                    self.logger.debug(
                        "Weapon change during compensation: %s -> %s",
                        self._last_weapon_for_compensation, weapon.name)
                    self._last_weapon_for_compensation = weapon.name

                self.weapon_change_event.clear()

                if self.input_service.is_key_pressed(key_trigger):
                    self.logger.debug("Starting compensation sequence")

                    compensation_completed = self._execute_compensation_sequence(
                        weapon, pattern, key_trigger)

                    if not compensation_completed and self.weapon_change_event.is_set():
                        continue

                    if compensation_completed:
                        while (self.input_service.is_key_pressed(key_trigger) and
                               not self.stop_event.is_set() and
                               not self.weapon_change_event.is_set()):
                            self.timing_service.combined_sleep_2(1)

                    if self.follow_rcs_overlay and self.follow_rcs_overlay.is_active:
                        self.follow_rcs_overlay.update_position(0.0, 0.0)

            except Exception as e:
                self.logger.error("Compensation loop error: %s", e, exc_info=True)

            self.timing_service.combined_sleep_2(1)

        self.logger.debug("Compensation loop terminated")

    def _execute_compensation_sequence(
            self,
            weapon: WeaponProfile,
            pattern: List,
            key_trigger: int) -> bool:
        """Execute complete compensation sequence for given weapon."""
        begin_time = self.timing_service.system_time()
        accumulated_time = 0.0

        self.accumulated_x = 0.0
        self.accumulated_y = 0.0
        self.raw_recoil_x = 0.0
        self.raw_recoil_y = 0.0

        if self.follow_rcs_overlay and self.follow_rcs_overlay.is_active:
            self.follow_rcs_overlay.update_position(0.0, 0.0)

        sum_x = 0.0
        sum_y = 0.0

        for i, point in enumerate(pattern):
            if self.weapon_change_event.is_set():
                self.logger.debug("Weapon change detected during sequence at index %s", i)
                return False

            if not self.input_service.is_key_pressed(key_trigger) or self.stop_event.is_set():
                self.logger.debug("Sequence interrupted at index %s", i)
                return False

            if i == 0:
                delay = point.delay / weapon.sleep_divider - weapon.sleep_suber
                accumulated_time = delay
                self.timing_service.combined_sleep(accumulated_time, begin_time)
                continue

            # Apply movement jitter if enabled (Gaussian distribution)
            jitter_factor = 1.0
            if weapon.jitter_movement > 0:
                # Gaussian jitter: std_dev = jitter% / 3 (99.7% within +/- jitter%)
                std_dev = (weapon.jitter_movement / 100.0) / 3.0
                jitter_factor = 1.0 + random.gauss(0, std_dev)

            # Apply jitter to raw recoil tracking
            jittered_dx = point.dx * jitter_factor
            jittered_dy = point.dy * jitter_factor

            self.raw_recoil_x += -jittered_dx
            self.raw_recoil_y += jittered_dy

            if self.follow_rcs_overlay and self.follow_rcs_overlay.is_active:
                self.follow_rcs_overlay.update_position(self.raw_recoil_x, self.raw_recoil_y)

            dx_float = jittered_dx
            dy_float = -jittered_dy

            sum_x += dx_float
            sum_y += dy_float

            dx_int = int(sum_x)
            dy_int = int(sum_y)

            sum_x -= dx_int
            sum_y -= dy_int

            if dx_int != 0 or dy_int != 0:
                self.input_service.mouse_move(dx_int, dy_int)
                self.accumulated_x += dx_int
                self.accumulated_y += dy_int

            if i < len(pattern) - 1:
                if i <= weapon.multiple:
                    intermediate_sleep = (point.delay / weapon.sleep_divider - weapon.sleep_suber) / 2
                else:
                    intermediate_sleep = (point.delay / weapon.sleep_divider - weapon.sleep_suber) * 2 / 3

                self.timing_service.combined_sleep_2(intermediate_sleep)

                # Apply timing jitter if enabled (Gaussian distribution)
                delay_time = point.delay / weapon.sleep_divider - weapon.sleep_suber
                if weapon.jitter_timing > 0:
                    # Gaussian jitter: std_dev = jitter_ms / 3 (99.7% within +/- jitter_ms)
                    std_dev = weapon.jitter_timing / 3.0
                    timing_jitter = random.gauss(0, std_dev)
                    delay_time += timing_jitter / 1000.0  # Convert ms to seconds

                accumulated_time += delay_time
                self.timing_service.combined_sleep(accumulated_time, begin_time)

        self.logger.debug("Compensation sequence completed normally")
        return True
