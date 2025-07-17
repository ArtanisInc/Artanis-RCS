"""
Recoil Compensation System.
"""
import sys
import logging
import time
import os
from typing import Tuple

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
import qdarktheme

from core.services.hotkey_service import HotkeyService, HotkeyAction
from core.services.tts_service import TTSService
from core.services.gsi_service import GSIService
from core.services.weapon_detection_service import WeaponDetectionService
from core.services.bomb_timer_service import BombTimerService
from core.services.auto_accept_service import AutoAcceptService


def setup_dark_theme(app: QApplication, theme: str = "dark") -> bool:
    """
    Setup PyQtDarkTheme with version compatibility.

    Args:
        app: QApplication instance
        theme: Theme name ("dark", "light", or "auto" if supported)

    Returns:
        bool: True if theme was applied successfully
    """
    try:
        if hasattr(qdarktheme, 'load_stylesheet'):
            if theme == "auto":
                theme = "dark"
            app.setStyleSheet(qdarktheme.load_stylesheet(theme))
            return True
        else:
            print("Warning: PyQtDarkTheme API methods not found")
            return False
    except Exception as e:
        print(f"Warning: Failed to apply PyQtDarkTheme: {e}")
        return False


def cleanup_log_file():
    """Clean up the log file at startup."""
    log_file = 'recoil_system.log'
    try:
        if os.path.exists(log_file):
            os.remove(log_file)
            print(f"Previous log file '{log_file}' cleaned up")
    except Exception as e:
        print(f"Warning: Could not clean up log file '{log_file}': {e}")


def setup_logging() -> logging.Logger:
    """Configure logging system."""
    # Clean up previous log file
    cleanup_log_file()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('recoil_system.log'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger("RecoilSystem")

    # Reduce verbosity of external libraries
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    logger.info("Logging system initialized")
    return logger


def initialize_system() -> Tuple:
    """Initialize all system services."""
    from data.config_repository import ConfigRepository, CSVRepository
    from core.services.config_service import ConfigService
    from core.services.input_service import InputService
    from core.services.recoil_service import RecoilService

    logger = logging.getLogger("Initialization")
    logger.info("Initializing system...")

    try:
        config_repository = ConfigRepository()
        csv_repository = CSVRepository()
        config_service = ConfigService(config_repository, csv_repository)
        input_service = InputService()

        features = config_service.config.get("features", {})
        tts_enabled = features.get("tts_enabled", True)
        tts_service = TTSService(enabled=tts_enabled)

        if tts_service.is_enabled():
            tts_service.set_voice_properties(rate=4, volume=65)

        recoil_service = RecoilService(
            config_service, input_service, tts_service)

        gsi_config = config_service.config.get("gsi", {})
        gsi_service = GSIService(
            host=gsi_config.get("server_host", "127.0.0.1"),
            port=gsi_config.get("server_port", 59873),
            gsi_config=gsi_config,
            auto_generate_config=True
        )
        weapon_detection_service = WeaponDetectionService(recoil_service)

        hotkey_service = HotkeyService(input_service, config_service)
        hotkey_service.set_weapon_detection_service(weapon_detection_service)

        recoil_service.set_weapon_detection_service(weapon_detection_service)

        if gsi_config.get("enabled", True):
            weapon_detection_service.configure(gsi_config)

        # Initialize bomb timer service
        bomb_timer_service = BombTimerService(config_service)

        # Initialize Auto Accept service
        auto_accept_service = AutoAcceptService(config_service, input_service, tts_service)

        # Connect GSI service to Auto Accept (for better path detection)
        auto_accept_service.set_gsi_service(gsi_service)

        # Log grouped services summary
        services_summary = [
            "Input",
            "Timing (10MHz/1ns)",
            "Recoil",
            "Weapon Detection",
            "Bomb Timer",
            "Auto Accept",
            f"Hotkeys ({len(hotkey_service.hotkey_mappings)} active)"
        ]
        logger.info("Core services initialized: %s", ", ".join(services_summary))

        logger.info("System initialized successfully")
        return (config_service, input_service, recoil_service, hotkey_service,
                tts_service, gsi_service, weapon_detection_service, bomb_timer_service, auto_accept_service)

    except Exception as e:
        logger.critical("System initialization failed: %s", e, exc_info=True)
        raise


def setup_gsi_integration(gsi_service: GSIService,
                          weapon_detection_service: WeaponDetectionService,
                          bomb_timer_service
                          ) -> bool:
    """Setup GSI integration and start services."""
    logger = logging.getLogger("GSIIntegration")

    try:
        gsi_service.register_callback(
            "weapon_detection",
            weapon_detection_service.process_player_state)

        gsi_service.register_callback(
            "bomb_timer",
            bomb_timer_service.process_player_state)

        if not gsi_service.start_server():
            logger.error("Failed to start GSI server")
            return False

        if not weapon_detection_service.enable():
            logger.error("Failed to enable weapon detection")
            return False

        logger.info("GSI integration ready: server started, weapon detection enabled")
        return True

    except Exception as e:
        logger.error("GSI integration setup failed: %s", e)
        return False


def create_gui(config_service, recoil_service, hotkey_service, tts_service,
               gsi_service=None, weapon_detection_service=None, bomb_timer_service=None, auto_accept_service=None):
    """Create main GUI window."""
    from ui.views.main_window import MainWindow

    logger = logging.getLogger("GUI")
    logger.debug("Creating GUI...")

    try:
        window = MainWindow(recoil_service, config_service)

        window.set_hotkey_service(hotkey_service)

        if gsi_service and weapon_detection_service:
            window.set_gsi_services(gsi_service, weapon_detection_service)

        if bomb_timer_service:
            window.set_bomb_timer_service(bomb_timer_service)

        if auto_accept_service:
            window.set_auto_accept_service(auto_accept_service)

        setup_hotkey_callbacks(window, recoil_service, hotkey_service,
                               tts_service, weapon_detection_service)

        logger.info("GUI initialized: Main window, Config tab, Visualization tab")
        return window

    except Exception as e:
        logger.critical("GUI creation failed: %s", e, exc_info=True)
        raise


def setup_hotkey_callbacks(main_window, recoil_service, hotkey_service,
                           tts_service, weapon_detection_service=None, auto_accept_service=None):
    """Configure hotkey callbacks with TTS coordination."""
    logger = logging.getLogger("HotkeySetup")

    def toggle_recoil_action():
        """Toggle recoil compensation."""
        try:
            if recoil_service.active:
                success = recoil_service.stop_compensation()
                if not success:
                    logger.error("Failed to stop compensation")
            else:
                current_weapon = recoil_service.current_weapon

                if not current_weapon:
                    current_weapon = main_window.config_tab.get_selected_weapon()

                if not current_weapon:
                    logger.warning("No weapon available")
                    tts_service.speak("No weapon available")
                    return

                if recoil_service.current_weapon != current_weapon:
                    recoil_service.set_weapon(current_weapon)

                success = recoil_service.start_compensation(
                    allow_manual_when_auto_enabled=False)

                if not success:
                    logger.error("Failed to start compensation")

            action_text = "started" if recoil_service.active else "stopped"
            logger.debug("Compensation %s via hotkey", action_text)

        except Exception as e:
            logger.error("Toggle compensation error: %s", e)

    def toggle_weapon_detection_action():
        """Toggle weapon detection GSI feature."""
        try:
            if weapon_detection_service:
                if weapon_detection_service.enabled:
                    success = weapon_detection_service.disable()
                    status_text = "disabled" if success else "disable failed"
                else:
                    success = weapon_detection_service.enable()
                    status_text = "enabled" if success else "enable failed"

                logger.debug("Weapon detection %s via hotkey", status_text)

                if success:
                    tts_service.speak(f"Weapon detection {status_text}")
                else:
                    logger.error("Failed to toggle weapon detection")
            else:
                logger.warning("Weapon detection service not available")

        except Exception as e:
            logger.error("Toggle weapon detection error: %s", e)

    def exit_action():
        """Exit application."""
        logger.debug("Closing application via hotkey")
        tts_service.speak("Closing script")
        time.sleep(1.5)
        main_window.close()

    def weapon_select_action(weapon_name: str):
        """Select weapon via hotkey with conditional TTS announcement."""
        try:
            weapon_combo = (main_window.config_tab.global_weapon_section
                            .weapon_combo)
            index = weapon_combo.findData(weapon_name)

            if index >= 0:
                weapon_combo.setCurrentIndex(index)
                recoil_service.set_weapon(weapon_name)

                # Only announce if automatic weapon detection is not active
                should_announce = True
                if (weapon_detection_service and
                        weapon_detection_service.enabled):
                    should_announce = False
                    logger.debug(
                        "Weapon selection TTS suppressed: auto detection active")

                if should_announce:
                    weapon_display = (main_window.config_service
                                      .get_weapon_display_name(weapon_name))
                    clean_name = weapon_display.replace(
                        "-", " ").replace("_", " ")
                    tts_service.speak(clean_name)

                logger.debug("Weapon selected via hotkey: %s", weapon_name)
            else:
                logger.warning("Weapon not found in UI: %s", weapon_name)

        except Exception as e:
            logger.error("Weapon selection error: %s", e)

    try:
        hotkey_service.register_action_callback(HotkeyAction.TOGGLE_RECOIL,
                                                toggle_recoil_action)
        hotkey_service.register_action_callback(
            HotkeyAction.TOGGLE_WEAPON_DETECTION,
            toggle_weapon_detection_action)
        hotkey_service.register_action_callback(HotkeyAction.EXIT,
                                                exit_action)
        hotkey_service.register_weapon_callback(weapon_select_action)

        hotkey_service.start_monitoring()
        logger.debug("Hotkey callbacks configured")

    except Exception as e:
        logger.error("Hotkey callback setup failed: %s", e)


def main():
    """Main entry point."""
    logger = setup_logging()

    try:
        app = QApplication(sys.argv)

        # Apply PyQtDarkTheme with version compatibility
        if not setup_dark_theme(app, "dark"):
            logger.warning("Failed to apply PyQtDarkTheme, using default styling")

        (config_service, input_service, recoil_service, hotkey_service,
         tts_service, gsi_service,
         weapon_detection_service, bomb_timer_service, auto_accept_service) = initialize_system()

        gsi_enabled = config_service.config.get("gsi", {}).get("enabled", True)
        if gsi_enabled:
            if not setup_gsi_integration(
                    gsi_service, weapon_detection_service, bomb_timer_service):
                logger.warning("GSI integration failed, continuing without it")
                gsi_service = None
                weapon_detection_service = None
        else:
            logger.info("GSI integration disabled in configuration")
            gsi_service = None
            weapon_detection_service = None

        window = create_gui(config_service, recoil_service, hotkey_service,
                            tts_service, gsi_service, weapon_detection_service,
                            bomb_timer_service, auto_accept_service)
        window.show()

        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(100)

        def cleanup_on_exit():
            """Clean shutdown with GSI cleanup."""
            logger.debug("Cleaning up on exit...")
            try:
                hotkey_service.stop_monitoring()
                if recoil_service.active:
                    recoil_service.stop_compensation()
                if weapon_detection_service:
                    weapon_detection_service.disable()
                if gsi_service:
                    gsi_service.stop_server()
                if bomb_timer_service:
                    bomb_timer_service.stop()
                if auto_accept_service:
                    auto_accept_service.disable()
                tts_service.stop()
            except Exception as e:
                logger.error("Cleanup error: %s", e)

        app.aboutToQuit.connect(cleanup_on_exit)

        logger.info("=== RCS System Started ===")
        tts_service.speak("RCS system ready")

        sys.exit(app.exec_())

    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        QMessageBox.critical(None, "Fatal Error",
                             f"A fatal error occurred: {e}")


if __name__ == "__main__":
    main()
