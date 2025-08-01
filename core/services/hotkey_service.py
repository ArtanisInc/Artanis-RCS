"""
Global hotkey management service with thread-safe monitoring.
"""
import logging
import threading
import time
import traceback
import queue
from typing import Dict, Callable, Optional, Any
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
    """Manages hotkey action callbacks with thread-safe execution.
    
    Note: UI callbacks must be dispatched to the main thread. This class provides
    thread-safe callback storage and execution mechanisms.
    """

    def __init__(self):
        self.action_callbacks: Dict[HotkeyAction, Callable] = {}
        self.weapon_callback: Optional[Callable[[str], None]] = None
        self.logger = logging.getLogger("CallbackManager")
        
        # Thread safety for callback storage
        self._callback_lock = threading.Lock()
        
        # Error callback mechanism for fatal background errors
        self.error_callback: Optional[Callable[[Exception, str], None]] = None
        
        # Thread-safe callback dispatch queue (for main thread execution)
        self.callback_queue: queue.Queue = queue.Queue()

    def set_error_callback(self, callback: Callable[[Exception, str], None]) -> None:
        """Set callback for fatal background errors.
        
        Args:
            callback: Function to handle exceptions with signature (exception, context)
        """
        with self._callback_lock:
            self.error_callback = callback
            self.logger.debug("Error callback registered")

    def register_action_callback(
            self,
            action: HotkeyAction,
            callback: Callable) -> None:
        """Register callback for system action.
        
        Args:
            action: The hotkey action to register
            callback: The callback function (must be thread-safe or dispatched to main thread)
        """
        with self._callback_lock:
            self.action_callbacks[action] = callback
            self.logger.debug("Action callback registered: %s", action.value)

    def register_weapon_callback(
            self, callback: Callable[[str], None]) -> None:
        """Register callback for weapon selection.
        
        Args:
            callback: The weapon callback function (must be thread-safe or dispatched to main thread)
        """
        with self._callback_lock:
            self.weapon_callback = callback
            self.logger.debug("Weapon callback registered")

    def queue_callback_for_main_thread(self, callback: Callable, *args, **kwargs) -> None:
        """Queue a callback to be executed in the main thread.
        
        This method provides a thread-safe way to dispatch callbacks that need
        to run in the main thread (e.g., UI operations).
        
        Args:
            callback: The callback function to execute
            *args: Positional arguments for the callback
            **kwargs: Keyword arguments for the callback
        """
        try:
            self.callback_queue.put((callback, args, kwargs), block=False)
        except queue.Full:
            self.logger.warning("Callback queue is full, dropping callback")

    def process_queued_callbacks(self) -> None:
        """Process all queued callbacks in the current thread.
        
        This should be called from the main thread to execute UI callbacks safely.
        """
        processed = 0
        try:
            while True:
                try:
                    callback, args, kwargs = self.callback_queue.get_nowait()
                    callback(*args, **kwargs)
                    processed += 1
                except queue.Empty:
                    break
                except Exception as e:
                    self.logger.error("Queued callback execution failed: %s", e, exc_info=True)
                    self._report_error(e, "queued_callback_execution")
        except Exception as e:
            self.logger.error("Error processing callback queue: %s", e, exc_info=True)
        
        if processed > 0:
            self.logger.debug("Processed %d queued callbacks", processed)

    def trigger_action(self, action: HotkeyAction) -> bool:
        """Trigger system action callback with thread safety.
        
        Args:
            action: The action to trigger
            
        Returns:
            bool: True if callback was found and queued/executed successfully
        """
        try:
            with self._callback_lock:
                callback = self.action_callbacks.get(action)
            
            if callback:
                # Queue for main thread execution due to potential UI interaction
                self.queue_callback_for_main_thread(callback)
                return True
            else:
                self.logger.warning(
                    "No callback registered for action: %s",
                    action.value)
                return False
        except Exception as e:
            self.logger.error(
                "Action callback queuing failed for %s: %s",
                action.value, e, exc_info=True)
            self._report_error(e, f"action_callback_{action.value}")
            return False

    def trigger_weapon_selection(self, weapon_name: str) -> bool:
        """Trigger weapon selection callback with thread safety.
        
        Args:
            weapon_name: The weapon name to select
            
        Returns:
            bool: True if callback was found and queued/executed successfully
        """
        try:
            with self._callback_lock:
                callback = self.weapon_callback
            
            if callback:
                # Queue for main thread execution due to potential UI interaction
                self.queue_callback_for_main_thread(callback, weapon_name)
                return True
            else:
                self.logger.warning(
                    "No weapon callback registered for: %s", weapon_name)
                return False
        except Exception as e:
            self.logger.error("Weapon callback queuing failed for %s: %s", 
                            weapon_name, e, exc_info=True)
            self._report_error(e, f"weapon_callback_{weapon_name}")
            return False

    def _report_error(self, exception: Exception, context: str) -> None:
        """Report a fatal background error to the main application.
        
        Args:
            exception: The exception that occurred
            context: Context description of where the error occurred
        """
        try:
            with self._callback_lock:
                error_callback = self.error_callback
            
            if error_callback:
                self.queue_callback_for_main_thread(error_callback, exception, context)
            else:
                self.logger.warning("No error callback registered for fatal error in %s", context)
        except Exception as e:
            self.logger.error("Failed to report error: %s", e, exc_info=True)


class HotkeyService:
    """Centralized hotkey management with thread-safe monitoring.
    
    This service provides thread-safe hotkey monitoring with proper synchronization
    of shared state and safe callback dispatching for UI interactions.
    
    Thread Safety Features:
    - Shared mutable data protected by threading locks
    - UI callbacks dispatched to main thread via queue mechanism
    - Enhanced exception handling with traceback logging
    - Graceful shutdown with timeout monitoring
    """

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

        # Shared mutable state - protected by locks
        self.hotkey_mappings: Dict[str, int] = {}
        self.weapon_hotkeys: Dict[str, str] = {}
        
        # Thread safety locks for shared state
        self._mappings_lock = threading.Lock()
        self._monitoring_lock = threading.Lock()
        
        # Error tracking for background threads
        self._background_errors: queue.Queue = queue.Queue()

        self._update_hotkey_mappings()
        self.logger.debug("Hotkey service initialized with thread safety")

    def set_error_callback(self, callback: Callable[[Exception, str], None]) -> None:
        """Set callback for fatal background errors.
        
        Args:
            callback: Function to handle exceptions from background threads
        """
        self.callback_manager.set_error_callback(callback)

    def process_background_callbacks(self) -> None:
        """Process queued callbacks in the main thread.
        
        This method should be called periodically from the main thread to execute
        UI callbacks safely. Recommended to call this from a QTimer or similar
        main thread event loop mechanism.
        """
        self.callback_manager.process_queued_callbacks()

    def _update_hotkey_mappings(self) -> None:
        """Update hotkey mappings from configuration with thread safety."""
        try:
            hotkeys = self.config_service.hotkeys
            
            # Create new mappings first
            new_hotkey_mappings: Dict[str, int] = {}
            new_weapon_hotkeys: Dict[str, str] = {}

            system_actions = [
                "toggle_recoil",
                "toggle_weapon_detection",
                "exit"]
            for action in system_actions:
                key_name = hotkeys.get(action)
                if key_name:
                    vk_code = self.input_service.get_key_code(key_name)
                    if vk_code:
                        new_hotkey_mappings[action] = vk_code

            weapon_names = set(self.config_service.weapon_profiles.keys())
            for weapon_name in weapon_names:
                key_name = hotkeys.get(weapon_name)
                if key_name:
                    vk_code = self.input_service.get_key_code(key_name)
                    if vk_code:
                        new_weapon_hotkeys[weapon_name] = key_name
                        new_hotkey_mappings[weapon_name] = vk_code

            # Atomically update shared state with lock protection
            with self._mappings_lock:
                self.hotkey_mappings.clear()
                self.weapon_hotkeys.clear()
                self.hotkey_mappings.update(new_hotkey_mappings)
                self.weapon_hotkeys.update(new_weapon_hotkeys)

            self.logger.debug(
                "Hotkey mappings updated: %s active", len(new_hotkey_mappings))

        except Exception as e:
            self.logger.error("Failed to update hotkey mappings: %s", e, exc_info=True)
            self._report_background_error(e, "hotkey_mappings_update")

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
        """Start hotkey monitoring thread with thread safety checks."""
        with self._monitoring_lock:
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
                self.logger.error("Failed to start hotkey monitoring: %s", e, exc_info=True)
                self._report_background_error(e, "monitoring_startup")
                return False

    def stop_monitoring(self) -> bool:
        """Stop hotkey monitoring thread with enhanced shutdown handling."""
        with self._monitoring_lock:
            if not self.is_monitoring:
                return True

            try:
                self.stop_event.set()

                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.monitoring_thread.join(timeout=2.0)
                    
                    # Enhanced graceful shutdown: check if thread is still alive
                    if self.monitoring_thread.is_alive():
                        self.logger.warning(
                            "Hotkey monitoring thread did not terminate within timeout (2.0s). "
                            "Thread may still be running. Consider checking for blocking operations."
                        )
                        # Set additional flag for emergency shutdown awareness
                        self._monitoring_shutdown_incomplete = True
                        # Note: We cannot force-kill the thread, but we've logged the issue
                    else:
                        self.logger.debug("Hotkey monitoring thread terminated gracefully")

                self.is_monitoring = False
                self.logger.debug("Hotkey monitoring stopped")
                return True

            except Exception as e:
                self.logger.error("Failed to stop hotkey monitoring: %s", e, exc_info=True)
                self._report_background_error(e, "monitoring_shutdown")
                return False

    def _monitoring_loop(self) -> None:
        """Main monitoring loop for hotkey detection with enhanced error handling."""
        self.logger.debug("Hotkey monitoring loop started")

        try:
            while not self.stop_event.is_set():
                try:
                    # Thread-safe access to hotkey mappings
                    with self._mappings_lock:
                        current_mappings = dict(self.hotkey_mappings)

                    # Check each configured hotkey
                    for identifier, vk_code in current_mappings.items():
                        if self.monitor.check_hotkey_triggered(
                                identifier, vk_code):
                            self._handle_hotkey_trigger(identifier)

                    # CPU-friendly polling
                    time.sleep(0.01)  # 10ms polling rate

                except Exception as e:
                    # Enhanced exception handling with full traceback
                    self.logger.error(
                        "Monitoring loop error: %s\nFull traceback:\n%s",
                        e, traceback.format_exc()
                    )
                    self._report_background_error(e, "monitoring_loop_iteration")
                    time.sleep(0.1)  # Longer pause on error

        except Exception as e:
            # Critical error in monitoring loop
            self.logger.critical(
                "Fatal error in hotkey monitoring loop: %s\nFull traceback:\n%s",
                e, traceback.format_exc()
            )
            self._report_background_error(e, "monitoring_loop_fatal")
        finally:
            self.logger.debug("Hotkey monitoring loop terminated")

    def set_weapon_detection_service(self, weapon_detection_service) -> None:
        """Set reference to weapon detection service for conditional processing."""
        self.weapon_detection_service = weapon_detection_service
        self.logger.debug(
            "Weapon detection service reference established for hotkey management")

    def _handle_hotkey_trigger(self, identifier: str) -> None:
        """Handle hotkey trigger event with conditional recoil and weapon hotkey processing.
        
        Enhanced with thread-safe execution and comprehensive error handling.
        """
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
            # Enhanced exception handling with full traceback
            self.logger.error(
                "Hotkey trigger handling failed for %s: %s\nFull traceback:\n%s", 
                identifier, e, traceback.format_exc())
            self._report_background_error(e, f"hotkey_trigger_{identifier}")

    def _report_background_error(self, exception: Exception, context: str) -> None:
        """Report background thread errors for main application awareness.
        
        Args:
            exception: The exception that occurred
            context: Context description of where the error occurred
        """
        try:
            self._background_errors.put((exception, context), block=False)
            # Also report through callback manager if available
            self.callback_manager._report_error(exception, context)
        except queue.Full:
            self.logger.warning("Background error queue is full, dropping error report")
        except Exception as e:
            self.logger.error("Failed to report background error: %s", e)

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
        """Reload hotkey configuration with thread safety."""
        try:
            with self._monitoring_lock:
                was_monitoring = self.is_monitoring

                if was_monitoring:
                    self.stop_monitoring()

                self._update_hotkey_mappings()

                if was_monitoring:
                    self.start_monitoring()

            self.logger.info("Hotkey configuration reloaded")

        except Exception as e:
            self.logger.error("Configuration reload failed: %s", e, exc_info=True)
            self._report_background_error(e, "configuration_reload")

    def get_background_errors(self) -> list:
        """Get any background errors that occurred.
        
        Returns:
            list: List of (exception, context) tuples for background errors
        """
        errors = []
        try:
            while True:
                try:
                    error = self._background_errors.get_nowait()
                    errors.append(error)
                except queue.Empty:
                    break
        except Exception as e:
            self.logger.error("Failed to retrieve background errors: %s", e)
        return errors

    def get_active_hotkey_count(self) -> int:
        """Get the number of active hotkey mappings in a thread-safe manner.
        
        Returns:
            int: Number of active hotkey mappings
        """
        with self._mappings_lock:
            return len(self.hotkey_mappings)
