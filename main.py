"""
Recoil Compensation System.
"""
import sys
import logging
import os
from typing import Tuple

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QMetaObject, Qt
import qdarktheme

from core.services.hotkey_service import HotkeyService, HotkeyAction
from core.services.tts_service import TTSService
from core.services.gsi_service import GSIService
from core.services.weapon_detection_service import WeaponDetectionService
from core.services.bomb_timer_service import BombTimerService
from core.services.auto_accept_service import AutoAcceptService


def setup_dark_theme(app: QApplication, theme: str = "dark") -> bool:
    """
    Setup qdarktheme with PySide6 compatibility.

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
            print("Warning: qdarktheme API methods not found")
            return False
    except Exception as e:
        print(f"Warning: Failed to apply qdarktheme: {e}")
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

        bomb_timer_service = BombTimerService(config_service)

        auto_accept_service = AutoAcceptService(config_service, input_service, tts_service)

        auto_accept_service.set_gsi_service(gsi_service)

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


def create_gui(app: QApplication, config_service, recoil_service, hotkey_service, tts_service,
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

        setup_hotkey_callbacks(app, window, recoil_service, hotkey_service,
                               tts_service, weapon_detection_service)

        logger.info("GUI initialized: Main window, Config tab, Visualization tab")
        return window

    except Exception as e:
        logger.critical("GUI creation failed: %s", e, exc_info=True)
        raise


def setup_hotkey_callbacks(app: QApplication, main_window, recoil_service, hotkey_service,
                           tts_service, weapon_detection_service=None, auto_accept_service=None):
    """Configure hotkey callbacks with TTS coordination."""
    logger = logging.getLogger("HotkeySetup")

    def toggle_recoil_action():
        """Toggle recoil compensation."""
        QMetaObject.invokeMethod(
            main_window,
            "toggle_recoil_action_slot",
            Qt.ConnectionType.QueuedConnection)

    def toggle_weapon_detection_action():
        """Toggle weapon detection GSI feature."""
        QMetaObject.invokeMethod(
            main_window,
            "toggle_weapon_detection_action_slot",
            Qt.ConnectionType.QueuedConnection)

    def exit_action():
        """Exit application."""
        logger.debug("Closing application via hotkey")
        QMetaObject.invokeMethod(app, 'quit', Qt.ConnectionType.QueuedConnection)
        tts_service.speak("Closing script")

    def weapon_select_action(weapon_name: str):
        """Select weapon via hotkey with conditional TTS announcement."""
        QMetaObject.invokeMethod(
            main_window,
            "weapon_select_action_slot",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, weapon_name))

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

        # Apply qdarktheme with version compatibility
        if not setup_dark_theme(app, "dark"):
            logger.warning("Failed to apply qdarktheme, using default styling")

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

        window = create_gui(app, config_service, recoil_service, hotkey_service,
                            tts_service, gsi_service, weapon_detection_service,
                            bomb_timer_service, auto_accept_service)
        window.show()

        timer = QTimer(app)
        timer.timeout.connect(lambda: None)
        timer.start(100)

        def cleanup_on_exit():
            """Clean shutdown with GSI cleanup."""
            logger.debug("Cleaning up on exit...")
            try:
                logger.debug("Stopping hotkey service...")
                hotkey_service.stop_monitoring()
                logger.debug("Hotkey service stopped.")
            except Exception as e:
                logger.error("Error stopping hotkey service: %s", e)

            try:
                if recoil_service.active:
                    logger.debug("Stopping recoil compensation...")
                    recoil_service.stop_compensation()
                    logger.debug("Recoil compensation stopped.")
            except Exception as e:
                logger.error("Error stopping recoil compensation: %s", e)

            try:
                if weapon_detection_service:
                    logger.debug("Disabling weapon detection service...")
                    weapon_detection_service.disable()
                    logger.debug("Weapon detection service disabled.")
            except Exception as e:
                logger.error("Error disabling weapon detection service: %s", e)

            try:
                if gsi_service:
                    logger.debug("Stopping GSI service...")
                    gsi_service.stop_server()
                    logger.debug("GSI service stopped.")
            except Exception as e:
                logger.error("Error stopping GSI service: %s", e)

            try:
                if bomb_timer_service:
                    logger.debug("Stopping bomb timer service...")
                    bomb_timer_service.stop()
                    logger.debug("Bomb timer service stopped.")
            except Exception as e:
                logger.error("Error stopping bomb timer service: %s", e)

            try:
                if auto_accept_service:
                    logger.debug("Disabling auto accept service...")
                    auto_accept_service.disable()
                    logger.debug("Auto accept service disabled.")
            except Exception as e:
                logger.error("Error disabling auto accept service: %s", e)

            try:
                logger.debug("Stopping TTS service...")
                tts_service.stop()
                logger.debug("TTS service stopped.")
            except Exception as e:
                logger.error("Error stopping TTS service: %s", e)
            logger.debug("Cleanup complete.")

        app.aboutToQuit.connect(cleanup_on_exit)

        logger.info("=== RCS System Started ===")
        tts_service.speak("RCS system ready")

        sys.exit(app.exec())

    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        QMessageBox.critical(None, "Fatal Error",
                             f"A fatal error occurred: {e}")


if __name__ == "__main__":
    main()
