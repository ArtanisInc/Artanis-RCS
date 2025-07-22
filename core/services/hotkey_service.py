"""
Global hotkey management service with thread-safe monitoring.
"""
import logging
import threading
import time
from typing import Dict, Callable, Optional
from enum import Enum

from core.services.input_service import InputService
from core.services.config_service import ConfigService


class HotkeyAction(Enum):
    """Available hotkey actions."""
    TOGGLE_RECOIL = "toggle_recoil"
    TOGGLE_WEAPON_DETECTION = "toggle_weapon_detection"
    EXIT = "exit"
    WEAPON_SELECT = "weapon_select"


class HotkeyMonitor:
    """Monitors keyboard state for hotkey detection."""

    def __init__(
            self,
            input_service: InputService,
            debounce_delay: float = 0.1):
        self.input_service = input_service
        self.debounce_delay = debounce_delay
        self.key_states: Dict[str, bool] = {}
        self.last_trigger_times: Dict[str, float] = {}
        self.logger = logging.getLogger("HotkeyMonitor")

    def check_hotkey_triggered(self, identifier: str, vk_code: int) -> bool:
        """Check if hotkey was triggered (with debounce)."""
        current_time = time.time()
        is_pressed = self.input_service.is_key_pressed(vk_code)
        was_pressed = self.key_states.get(identifier, False)

        if is_pressed and not was_pressed:
            last_trigger = self.last_trigger_times.get(identifier, 0)
            if current_time - last_trigger >= self.debounce_delay:
                self.last_trigger_times[identifier] = current_time
                self.key_states[identifier] = is_pressed
                return True

        self.key_states[identifier] = is_pressed
        return False


class CallbackManager:
    """Manages hotkey action callbacks."""

    def __init__(self):
        self.action_callbacks: Dict[HotkeyAction, Callable] = {}
        self.weapon_callbacks: Dict[str, Callable[[str], None]] = {}
        self.logger = logging.getLogger("CallbackManager")

    def register_action_callback(
            self,
            action: HotkeyAction,
            callback: Callable) -> None:
        """Register callback for system action."""
        self.action_callbacks[action] = callback
        self.logger.debug("Action callback registered: %s", action.value)

    def register_weapon_callback(
            self, callback: Callable[[str], None]) -> None:
        """Register callback for weapon selection."""
        self.weapon_callback = callback
        self.logger.debug("Weapon callback registered")

    def trigger_action(self, action: HotkeyAction) -> bool:
        """Trigger system action callback."""
        try:
            callback = self.action_callbacks.get(action)
            if callback:
                callback()
                return True
            else:
                self.logger.warning(
                    "No callback registered for action: %s",
                    action.value)
                return False
        except Exception as e:
            self.logger.error(
                "Action callback failed for %s: %s",
                action.value, e)
            return False

    def trigger_weapon_selection(self, weapon_name: str) -> bool:
        """Trigger weapon selection callback."""
        try:
            if hasattr(self, 'weapon_callback') and self.weapon_callback:
                self.weapon_callback(weapon_name)
                return True
            else:
                self.logger.warning(
                    "No weapon callback registered for: %s", weapon_name)
                return False
        except Exception as e:
            self.logger.error("Weapon callback failed for %s: %s", weapon_name, e)
            return False


class HotkeyService:
    """Centralized hotkey management with thread-safe monitoring."""

    def __init__(self, input_service: InputService,
                 config_service: ConfigService):
        self.logger = logging.getLogger("HotkeyService")
        self.input_service = input_service
        self.config_service = config_service

        self.weapon_detection_service = None

        self.monitor = HotkeyMonitor(input_service)
        self.callback_manager = CallbackManager()

        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_monitoring = False

        self.hotkey_mappings: Dict[str, int] = {}
        self.weapon_hotkeys: Dict[str, str] = {}

        self._update_hotkey_mappings()
        self.logger.debug("Hotkey service initialized")

    def _update_hotkey_mappings(self) -> None:
        """Update hotkey mappings from configuration."""
        try:
            hotkeys = self.config_service.hotkeys
            self.hotkey_mappings.clear()
            self.weapon_hotkeys.clear()

            system_actions = [
                "toggle_recoil",
                "toggle_weapon_detection",
                "exit"]
            for action in system_actions:
                key_name = hotkeys.get(action)
                if key_name:
                    vk_code = self.input_service.get_key_code(key_name)
                    if vk_code:
                        self.hotkey_mappings[action] = vk_code

            weapon_names = set(self.config_service.weapon_profiles.keys())
            for weapon_name in weapon_names:
                key_name = hotkeys.get(weapon_name)
                if key_name:
                    vk_code = self.input_service.get_key_code(key_name)
                    if vk_code:
                        self.weapon_hotkeys[weapon_name] = key_name
                        self.hotkey_mappings[weapon_name] = vk_code

            self.logger.debug(
                "Hotkey mappings updated: %s active", len(self.hotkey_mappings))

        except Exception as e:
            self.logger.error("Failed to update hotkey mappings: %s", e)

    def register_action_callback(
            self,
            action: HotkeyAction,
            callback: Callable) -> None:
        """Register callback for system action."""
        self.callback_manager.register_action_callback(action, callback)

    def register_weapon_callback(
            self, callback: Callable[[str], None]) -> None:
        """Register callback for weapon selection."""
        self.callback_manager.register_weapon_callback(callback)

    def start_monitoring(self) -> bool:
        """Start hotkey monitoring thread."""
        if self.is_monitoring:
            self.logger.warning("Hotkey monitoring already active")
            return False

        try:
            self._update_hotkey_mappings()

            self.stop_event.clear()
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="HotkeyMonitor"
            )
            self.monitoring_thread.start()

            self.is_monitoring = True
            self.logger.debug("Hotkey monitoring started")
            return True

        except Exception as e:
            self.logger.error("Failed to start hotkey monitoring: %s", e)
            return False

    def stop_monitoring(self) -> bool:
        """Stop hotkey monitoring thread."""
        if not self.is_monitoring:
            return True

        try:
            self.stop_event.set()

            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2.0)

            self.is_monitoring = False
            self.logger.debug("Hotkey monitoring stopped")
            return True

        except Exception as e:
            self.logger.error("Failed to stop hotkey monitoring: %s", e)
            return False

    def _monitoring_loop(self) -> None:
        """Main monitoring loop for hotkey detection."""
        self.logger.debug("Hotkey monitoring loop started")

        while not self.stop_event.is_set():
            try:
                # Check each configured hotkey
                for identifier, vk_code in self.hotkey_mappings.items():
                    if self.monitor.check_hotkey_triggered(
                            identifier, vk_code):
                        self._handle_hotkey_trigger(identifier)

                # CPU-friendly polling
                time.sleep(0.01)  # 10ms polling rate

            except Exception as e:
                self.logger.error("Monitoring loop error: %s", e)
                time.sleep(0.1)  # Longer pause on error

        self.logger.debug("Hotkey monitoring loop terminated")

    def set_weapon_detection_service(self, weapon_detection_service) -> None:
        """Set reference to weapon detection service for conditional processing."""
        self.weapon_detection_service = weapon_detection_service
        self.logger.debug(
            "Weapon detection service reference established for hotkey management")

    def _handle_hotkey_trigger(self, identifier: str) -> None:
        """Handle hotkey trigger event with conditional recoil and weapon hotkey processing."""
        try:
            self.logger.debug("Hotkey triggered: %s", identifier)

            # System actions
            if identifier == "toggle_recoil":
                # Vérifier si l'activation manuelle est autorisée
                if self._should_process_recoil_hotkey():
                    self.callback_manager.trigger_action(
                        HotkeyAction.TOGGLE_RECOIL)
                else:
                    self.logger.info(
                        "Recoil toggle hotkey ignored: automatic weapon detection active")
            elif identifier == "toggle_weapon_detection":
                self.callback_manager.trigger_action(
                    HotkeyAction.TOGGLE_WEAPON_DETECTION)
            elif identifier == "exit":
                self.callback_manager.trigger_action(HotkeyAction.EXIT)

            # Weapon selection - conditionnellement désactivée
            elif identifier in self.config_service.weapon_profiles:
                if self._should_process_weapon_hotkey():
                    self.callback_manager.trigger_weapon_selection(identifier)
                else:
                    self.logger.info(
                        "Weapon hotkey '%s' ignored: automatic detection active", identifier)

            else:
                self.logger.warning("Unknown hotkey identifier: %s", identifier)

        except Exception as e:
            self.logger.error(
                "Hotkey trigger handling failed for %s: %s", identifier, e)

    def _should_process_recoil_hotkey(self) -> bool:
        """Determine if recoil toggle hotkey should be processed based on detection service state."""
        # Si le service de détection n'est pas disponible, toujours autoriser
        if not self.weapon_detection_service:
            return True

        # Si la détection automatique est active, désactiver le hotkey de compensation
        if self.weapon_detection_service.enabled:
            self.logger.debug(
                "Recoil hotkey disabled: automatic weapon detection active")
            return False

        return True

    def _should_process_weapon_hotkey(self) -> bool:
        """Determine if weapon hotkeys should be processed based on detection service state."""
        # Si le service de détection n'est pas disponible, toujours autoriser
        if not self.weapon_detection_service:
            return True

        # Si la détection automatique est active, désactiver les hotkeys
        # manuelles
        if self.weapon_detection_service.enabled:
            self.logger.debug(
                "Weapon hotkeys disabled: automatic weapon detection active")
            return False

        return True

    def reload_configuration(self) -> None:
        """Reload hotkey configuration."""
        try:
            was_monitoring = self.is_monitoring

            if was_monitoring:
                self.stop_monitoring()

            self._update_hotkey_mappings()

            if was_monitoring:
                self.start_monitoring()

            self.logger.info("Hotkey configuration reloaded")

        except Exception as e:
            self.logger.error("Configuration reload failed: %s", e)
