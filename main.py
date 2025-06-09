"""
Recoil Compensation System.
"""
import sys
import logging
import time
from typing import Tuple

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

from core.services.hotkey_service import HotkeyService, HotkeyAction
from core.services.tts_service import TTSService, TTSPriority
from core.services.gsi_service import GSIService
from core.services.weapon_detection_service import WeaponDetectionService


def setup_logging() -> logging.Logger:
    """Configure logging system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('recoil_system.log'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger("RecoilSystem")
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

        gsi_service = GSIService()
        weapon_detection_service = WeaponDetectionService(recoil_service)

        hotkey_service = HotkeyService(input_service, config_service)
        hotkey_service.set_weapon_detection_service(weapon_detection_service)

        recoil_service.set_weapon_detection_service(weapon_detection_service)

        gsi_config = config_service.config.get("gsi", {})
        if gsi_config.get("enabled", True):
            weapon_detection_service.configure(gsi_config)

        logger.info(
            "System initialized successfully with conditional hotkey management")
        return (config_service, input_service, recoil_service, hotkey_service,
                tts_service, gsi_service, weapon_detection_service)

    except Exception as e:
        logger.critical("System initialization failed: %s", e, exc_info=True)
        raise


def setup_gsi_integration(gsi_service: GSIService,
                          weapon_detection_service: WeaponDetectionService
                          ) -> bool:
    """Setup GSI integration and start services."""
    logger = logging.getLogger("GSIIntegration")

    try:
        gsi_service.register_callback(
            "weapon_detection",
            weapon_detection_service.process_player_state)

        if not gsi_service.start_server():
            logger.error("Failed to start GSI server")
            return False

        if not weapon_detection_service.enable():
            logger.error("Failed to enable weapon detection")
            return False

        logger.info("GSI integration setup completed")
        return True

    except Exception as e:
        logger.error("GSI integration setup failed: %s", e)
        return False


def create_gui(config_service, recoil_service, hotkey_service, tts_service,
               gsi_service=None, weapon_detection_service=None):
    """Create main GUI window with GSI integration."""
    from ui.views.main_window import MainWindow

    logger = logging.getLogger("GUI")
    logger.info("Creating GUI with GSI integration...")

    try:
        window = MainWindow(recoil_service, config_service)

        window.set_hotkey_service(hotkey_service)

        if gsi_service and weapon_detection_service:
            window.set_gsi_services(gsi_service, weapon_detection_service)

        setup_hotkey_callbacks(window, recoil_service, hotkey_service,
                               tts_service, weapon_detection_service)

        logger.info("GUI created successfully with GSI")
        return window

    except Exception as e:
        logger.critical("GUI creation failed: %s", e, exc_info=True)
        raise


def setup_hotkey_callbacks(main_window, recoil_service, hotkey_service,
                           tts_service, weapon_detection_service=None):
    """Configure hotkey callbacks with TTS coordination."""
    logger = logging.getLogger("HotkeySetup")

    def toggle_recoil_action():
        """Toggle recoil compensation."""
        try:
            if recoil_service.active:
                success = recoil_service.stop_compensation()
                if not success:
                    tts_service.speak("Stop error", TTSPriority.CRITICAL)
            else:
                current_weapon = recoil_service.current_weapon

                if not current_weapon:
                    current_weapon = main_window.config_tab.get_selected_weapon()

                if not current_weapon:
                    logger.warning(
                        "No weapon available for hotkey start (GSI or manual)")
                    # Always announce critical errors regardless of detection
                    # mode
                    tts_service.speak("No weapon available", TTSPriority.HIGH)
                    return

                if recoil_service.current_weapon != current_weapon:
                    recoil_service.set_weapon(current_weapon)

                success = recoil_service.start_compensation()
                if success and weapon_detection_service:
                    # Mark that user has manually initiated RCS
                    weapon_detection_service.set_user_initiated_start(True)

                if not success:
                    tts_service.speak("Start error", TTSPriority.CRITICAL)

            action_text = "started" if recoil_service.active else "stopped"
            logger.info("Compensation %s via hotkey", action_text)

        except Exception as e:
            logger.error("Toggle compensation error: %s", e)
            tts_service.speak("System error", TTSPriority.CRITICAL)

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

                logger.info("Weapon detection %s via hotkey", status_text)

                if success:
                    tts_service.speak(f"Weapon detection {status_text}",
                                      TTSPriority.HIGH)
                else:
                    tts_service.speak("Detection error", TTSPriority.CRITICAL)
            else:
                logger.warning("Weapon detection service not available")
                tts_service.speak("Detection unavailable", TTSPriority.HIGH)

        except Exception as e:
            logger.error("Toggle weapon detection error: %s", e)
            tts_service.speak("Detection error", TTSPriority.CRITICAL)

    def exit_action():
        """Exit application."""
        logger.info("Closing application via hotkey")
        tts_service.speak("Closing script", TTSPriority.HIGH)
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
                    tts_service.speak_interrupt_previous(clean_name,
                                                         TTSPriority.HIGH)

                logger.info("Weapon selected via hotkey: %s", weapon_name)
            else:
                logger.warning("Weapon not found in UI: %s", weapon_name)
                tts_service.speak("Weapon not found", TTSPriority.HIGH)

        except Exception as e:
            logger.error("Weapon selection error: %s", e)
            tts_service.speak("Selection error", TTSPriority.HIGH)

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
        logger.info("Hotkey callbacks configured with TTS coordination")

    except Exception as e:
        logger.error("Hotkey callback setup failed: %s", e)


def main():
    """Main entry point with GSI integration."""
    logger = setup_logging()

    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')

        (config_service, input_service, recoil_service, hotkey_service,
         tts_service, gsi_service,
         weapon_detection_service) = initialize_system()

        gsi_enabled = config_service.config.get("gsi", {}).get("enabled", True)
        if gsi_enabled:
            if not setup_gsi_integration(
                    gsi_service, weapon_detection_service):
                logger.warning("GSI integration failed, continuing without it")
                gsi_service = None
                weapon_detection_service = None
        else:
            logger.info("GSI integration disabled in configuration")
            gsi_service = None
            weapon_detection_service = None

        window = create_gui(config_service, recoil_service, hotkey_service,
                            tts_service, gsi_service, weapon_detection_service)
        window.show()

        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(100)

        def cleanup_on_exit():
            """Clean shutdown with GSI cleanup."""
            logger.info("Cleaning up on exit...")
            try:
                hotkey_service.stop_monitoring()
                if recoil_service.active:
                    recoil_service.stop_compensation()
                if weapon_detection_service:
                    weapon_detection_service.disable()
                if gsi_service:
                    gsi_service.stop_server()
                tts_service.stop()
            except Exception as e:
                logger.error("Cleanup error: %s", e)

        app.aboutToQuit.connect(cleanup_on_exit)

        if gsi_service:
            logger.info("=== RCS System with GSI Integration Started ===")
            tts_service.speak("RCS system with weapon detection ready",
                              TTSPriority.HIGH)
        else:
            logger.info("=== RCS System Started (GSI Disabled) ===")
            tts_service.speak("RCS system ready", TTSPriority.HIGH)

        sys.exit(app.exec_())

    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        QMessageBox.critical(None, "Fatal Error",
                             f"A fatal error occurred: {e}")


if __name__ == "__main__":
    main()
