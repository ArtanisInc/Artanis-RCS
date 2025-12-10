"""
Main application window with modular architecture.
"""
import logging
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QTabWidget,
    QGroupBox, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QFont
import qtawesome as qta

from core.services.recoil_service import RecoilService
from core.services.config_service import ConfigService
from ui.views.config_tab import ConfigTab
from ui.views.visualization_tab import VisualizationTab
from ui.widgets.bomb_timer_overlay import BombTimerOverlay


class ControlPanel:
    """Control panel for main system operations."""

    def __init__(self):
        self.group_box = QGroupBox("System Control")
        self._setup_ui()

    def _setup_ui(self):
        """Setup control panel UI with four distinct sections."""
        layout = QHBoxLayout(self.group_box)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 12, 16, 12)

        status_frame = self._create_status_section()
        layout.addWidget(status_frame)

        # Manual Controls section
        controls_frame = self._create_controls_section()
        layout.addWidget(controls_frame)

        # Auto Detection RCS section
        auto_detection_frame = self._create_auto_detection_section()
        layout.addWidget(auto_detection_frame)

        gsi_frame = self._create_gsi_status_section()
        layout.addWidget(gsi_frame)

        # Equal distribution
        layout.setStretchFactor(status_frame, 1)
        layout.setStretchFactor(controls_frame, 1)
        layout.setStretchFactor(auto_detection_frame, 1)
        layout.setStretchFactor(gsi_frame, 1)

    def _create_status_section(self) -> QFrame:
        """Create RCS status display section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("RCS Status")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title)

        # Status with color indicator
        status_container = QHBoxLayout()
        status_container.setSpacing(6)
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: #f44336;
                border-radius: 6px;
            }
        """)
        self.status_text = QLabel("Inactive")
        self.status_text.setFont(QFont("Arial", 9))
        status_container.addWidget(self.status_indicator)
        status_container.addWidget(self.status_text)
        status_container.addStretch()
        layout.addLayout(status_container)

        self.weapon_label = QLabel("Selected weapon: None")
        self.weapon_label.setFont(QFont("Arial", 9))
        self.weapon_label.setMinimumHeight(20)
        self.weapon_label.setWordWrap(True)
        self.weapon_label.setMinimumWidth(150)
        layout.addWidget(self.weapon_label)

        layout.addStretch()
        return frame

    def _create_controls_section(self) -> QFrame:
        """Create control buttons section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        title = QLabel("Manual RCS")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)

        self.start_button = self._create_action_button(
            "Start", "#4CAF50", "#45a049")
        self.stop_button = self._create_action_button(
            "Stop", "#f44336", "#da190b")
        self.stop_button.setEnabled(False)

        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        layout.addLayout(buttons_layout)
        layout.addStretch()

        return frame

    def _create_auto_detection_section(self) -> QFrame:
        """Create auto detection controls section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        title = QLabel("Auto Detection RCS")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)

        self.enable_detection_button = self._create_action_button(
            "Enable", "#4CAF50", "#45a049")
        self.disable_detection_button = self._create_action_button(
            "Disable", "#f44336", "#da190b")
        self.disable_detection_button.setEnabled(False)

        buttons_layout.addWidget(self.enable_detection_button)
        buttons_layout.addWidget(self.disable_detection_button)
        layout.addLayout(buttons_layout)
        layout.addStretch()

        return frame

    def _create_gsi_status_section(self) -> QFrame:
        """Create dedicated GSI status display section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("GSI Status")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title)

        # GSI connection status with color indicator
        gsi_container = QHBoxLayout()
        gsi_container.setSpacing(6)
        self.gsi_indicator = QLabel()
        self.gsi_indicator.setFixedSize(12, 12)
        self.gsi_indicator.setStyleSheet("""
            QLabel {
                background-color: #9e9e9e;
                border-radius: 6px;
            }
        """)
        self.gsi_text = QLabel("GSI: Disabled")
        self.gsi_text.setFont(QFont("Arial", 9))
        self.gsi_text.setMinimumWidth(120)
        gsi_container.addWidget(self.gsi_indicator)
        gsi_container.addWidget(self.gsi_text)
        gsi_container.addStretch()
        layout.addLayout(gsi_container)

        # Weapon detection status with color indicator
        detection_container = QHBoxLayout()
        detection_container.setSpacing(6)
        self.detection_indicator = QLabel()
        self.detection_indicator.setFixedSize(12, 12)
        self.detection_indicator.setStyleSheet("""
            QLabel {
                background-color: #9e9e9e;
                border-radius: 6px;
            }
        """)
        self.detection_text = QLabel("Detection: Disabled")
        self.detection_text.setFont(QFont("Arial", 9))
        self.detection_text.setMinimumWidth(130)
        self.detection_text.setWordWrap(True)
        detection_container.addWidget(self.detection_indicator)
        detection_container.addWidget(self.detection_text)
        detection_container.addStretch()
        layout.addLayout(detection_container)

        layout.addStretch()
        return frame

    def _create_action_button(
            self,
            text: str,
            bg_color: str,
            hover_color: str) -> QPushButton:
        """Create action button with specific colors."""
        button = QPushButton(text)
        button.setMinimumHeight(32)
        button.setMinimumWidth(70)
        button.setFont(QFont("Arial", 9, QFont.Weight.Bold))

        # Apply specific colors for action buttons
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #888888;
            }}
        """)

        return button


class MainWindow(QMainWindow):
    """Main application window."""
    gsi_status_update_signal = Signal()
    status_update_signal = Signal(dict)
    exit_requested_signal = Signal()  # Signal for exit hotkey

    def __init__(
            self,
            recoil_service: RecoilService,
            config_service: ConfigService):
        super().__init__()

        self.logger = logging.getLogger("MainWindow")
        self.recoil_service = recoil_service
        self.config_service = config_service

        # Simple flags for preventing signal loops (replaces WeaponStateService)
        self._updating_from_gsi = False
        self._updating_ui_only = False

        # Service references
        self.hotkey_service = None
        self.gsi_service = None
        self.weapon_detection_service = None
        self.bomb_timer_service = None
        self.auto_accept_service = None
        self.follow_rcs_overlay = None

        self.control_panel = ControlPanel()

        self.bomb_timer_overlay = BombTimerOverlay()

        self._setup_ui()
        self._setup_connections()

        # Connect signal for thread-safe status updates
        self.status_update_signal.connect(self._update_status)

        # Connect exit signal
        self.exit_requested_signal.connect(self._handle_exit_request)

        # Register status callback with recoil service
        self.recoil_service.register_status_changed_callback(
            self._on_status_changed_callback)

        self.logger.debug("Main window initialized")

    def set_hotkey_service(self, hotkey_service):
        """Set hotkey service reference for hot reload capability."""
        self.hotkey_service = hotkey_service
        self.logger.debug("Hotkey service reference established")

    def set_gsi_services(self, gsi_service, weapon_detection_service):
        """Set GSI service references for comprehensive monitoring."""
        self.gsi_service = gsi_service
        self.weapon_detection_service = weapon_detection_service
        self.logger.debug("GSI services integrated for status monitoring")

        self.update_weapon_detection_status()

        self._sync_initial_ui_state()

    def set_follow_rcs_overlay(self, follow_rcs_overlay):
        """Set follow RCS overlay reference."""
        self.follow_rcs_overlay = follow_rcs_overlay
        self.config_tab.set_follow_rcs_overlay(follow_rcs_overlay)
        self.logger.debug("Follow RCS overlay reference set")

    def set_bomb_timer_service(self, bomb_timer_service):
        """Set bomb timer service and connect overlay."""
        self.bomb_timer_service = bomb_timer_service

        bomb_timer_service.set_timer_update_callback(
            self.bomb_timer_overlay.update_bomb_state
        )

        self.logger.debug("Bomb timer service connected to overlay")

    def set_auto_accept_service(self, auto_accept_service):
        """Set auto accept service reference."""
        self.auto_accept_service = auto_accept_service
        self.logger.debug("Auto accept service reference set")

    def _sync_initial_ui_state(self):
        """Synchronize UI with initial service states after full initialization."""
        try:
            # Trigger a normal status notification to sync button states
            # This ensures we use the real-time state instead of a snapshot
            self.recoil_service._notify_status_changed()
            self.logger.debug("Initial UI state synchronized with services")
        except Exception as e:
            self.logger.error(f"Initial UI state synchronization error: {e}")

    def _setup_ui(self):
        """Setup main UI layout with improved styling."""
        self.setWindowTitle("Artanis's RCS")
        flags = (Qt.Window | Qt.WindowTitleHint |  # type: ignore
                Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)  # type: ignore
        self.setWindowFlags(flags)

        # Let qdarktheme handle styling

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Control panel with four sections
        main_layout.addWidget(self.control_panel.group_box)

        # UI separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)

        # Tab widget for configuration and visualization
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        self.config_tab = ConfigTab(self.config_service)
        self.visualization_tab = VisualizationTab(self.config_service)

        self.tabs.addTab(self.config_tab, qta.icon('fa5s.cog'), "Configuration")
        self.tabs.addTab(self.visualization_tab, qta.icon('fa5s.chart-bar'), "Visualization")
        main_layout.addWidget(self.tabs)

        # Fixed window dimensions like before
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def _setup_connections(self):
        """Setup signal-slot connections."""
        self.control_panel.start_button.clicked.connect(self._start_compensation)
        self.control_panel.stop_button.clicked.connect(self._stop_compensation)
        self.control_panel.enable_detection_button.clicked.connect(self._enable_auto_detection)
        self.control_panel.disable_detection_button.clicked.connect(self._disable_auto_detection)

        self.config_tab.weapon_changed.connect(self._on_weapon_changed)
        self.config_tab.settings_saved.connect(self._on_settings_saved)
        self.config_tab.hotkeys_updated.connect(self._on_hotkeys_updated)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.gsi_status_update_signal.connect(self.update_weapon_detection_status)

    def _on_weapon_changed(self, weapon_name: str):
        """Handle weapon selection change event from config tab."""
        # Skip processing if currently updating from GSI
        if self._updating_from_gsi:
            self.logger.debug("Skipping weapon change during GSI update")
            return

        try:
            if self.recoil_service.current_weapon != weapon_name:
                self.recoil_service.set_weapon(weapon_name)

            if weapon_name:
                self.visualization_tab.update_weapon_visualization(weapon_name)
            else:
                self.visualization_tab.update_weapon_visualization(None)

            self.logger.debug(f"Weapon changed from user: {weapon_name}")

            # Announce weapon change if not in auto-detection mode
            should_announce = True
            if (self.weapon_detection_service and
                    self.weapon_detection_service.enabled):
                should_announce = False

            if should_announce and weapon_name:
                weapon_display = (self.config_service
                                    .get_weapon_display_name(weapon_name))
                if weapon_display is not None:
                    clean_name = weapon_display.replace(
                        "-", " ").replace("_", " ")
                    tts_service = getattr(self.recoil_service, 'tts_service', None)
                    if tts_service is not None:
                        tts_service.speak(clean_name)

        except Exception as e:
            self.logger.error(f"Weapon change handling error: {e}")

    def _start_compensation(self):
        """Start recoil compensation with validation and error handling."""
        try:
            weapon_name = self.config_tab.get_selected_weapon()
            if not weapon_name:
                QMessageBox.warning(self, "Warning", "Please select a weapon")
                return

            if self.recoil_service.current_weapon != weapon_name:
                self.recoil_service.set_weapon(weapon_name)

            success = self.recoil_service.start_compensation()

            if success:
                self.control_panel.start_button.setEnabled(False)
                self.control_panel.stop_button.setEnabled(True)
                self.logger.debug(f"Compensation started for weapon: {weapon_name}")
            else:
                QMessageBox.warning(
                    self, "Warning", "Failed to start compensation")

        except Exception as e:
            self.logger.error(f"Start compensation error: {e}")
            QMessageBox.critical(self, "Error", f"Start error: {e}")

    def _stop_compensation(self):
        """Stop recoil compensation with status update."""
        try:
            success = self.recoil_service.stop_compensation()

            if success:
                self.control_panel.start_button.setEnabled(True)
                self.control_panel.stop_button.setEnabled(False)
                self.logger.debug("Compensation stopped")
            else:
                QMessageBox.warning(
                    self, "Warning", "Failed to stop compensation")

        except Exception as e:
            self.logger.error(f"Stop compensation error: {e}")
            QMessageBox.critical(self, "Error", f"Stop error: {e}")

    def _enable_auto_detection(self):
        """Enable automatic weapon detection."""
        try:
            if not self.weapon_detection_service:
                QMessageBox.warning(self, "Warning", "Weapon detection service not available")
                return

            if not self.gsi_service:
                QMessageBox.warning(self, "Warning", "GSI service not available")
                return

            # Enable GSI service first if not running
            if not self.gsi_service.is_running:
                success = self.gsi_service.start_server()
                if not success:
                    QMessageBox.warning(self, "Warning", "Failed to start GSI service")
                    return

            # Enable weapon detection
            success = self.weapon_detection_service.enable()
            if success:
                self.control_panel.enable_detection_button.setEnabled(False)
                self.control_panel.disable_detection_button.setEnabled(True)
                self.logger.debug("Auto weapon detection enabled")

                # TTS announcement
                tts_service = getattr(self.recoil_service, 'tts_service', None)
                if tts_service is not None:
                    tts_service.speak("Weapon detection enabled")
            else:
                QMessageBox.warning(self, "Warning", "Failed to enable weapon detection")

        except Exception as e:
            self.logger.error(f"Enable auto detection error: {e}")
            QMessageBox.critical(self, "Error", f"Enable error: {e}")

    def _disable_auto_detection(self):
        """Disable automatic weapon detection."""
        try:
            if not self.weapon_detection_service:
                QMessageBox.warning(self, "Warning", "Weapon detection service not available")
                return

            success = self.weapon_detection_service.disable()
            if success:
                self.control_panel.enable_detection_button.setEnabled(True)
                self.control_panel.disable_detection_button.setEnabled(False)
                self.logger.debug("Auto weapon detection disabled")

                # TTS announcement
                tts_service = getattr(self.recoil_service, 'tts_service', None)
                if tts_service is not None:
                    tts_service.speak("Weapon detection disabled")
            else:
                QMessageBox.warning(self, "Warning", "Failed to disable weapon detection")

        except Exception as e:
            self.logger.error(f"Disable auto detection error: {e}")
            QMessageBox.critical(self, "Error", f"Disable error: {e}")

    def sync_ui_with_gsi_weapon(self, weapon_name: str) -> None:
        """Synchronize UI weapon selection with GSI detected weapon."""
        try:
            if self._updating_ui_only:
                self.logger.debug("Skipping GSI weapon sync during UI update")
                return

            self._updating_from_gsi = True

            weapon_combo = self.config_tab.active_weapon_section.weapon_combo

            if not weapon_name:
                weapon_combo.setCurrentIndex(0)
                self.config_tab.weapon_parameters_section.multiple_spin.setValue(0)
                self.config_tab.weapon_parameters_section.sleep_divider_spin.setValue(1.0)
                self.config_tab.weapon_parameters_section.sleep_suber_spin.setValue(0.0)
                self.visualization_tab._clear_visualization()
                self.logger.debug("UI weapon selection cleared from GSI")
            else:
                index = weapon_combo.findData(weapon_name)
                if index >= 0:
                    weapon_combo.setCurrentIndex(index)

                    weapon = self.config_service.get_weapon_profile(weapon_name)
                    if weapon:
                        self.config_tab.weapon_parameters_section.multiple_spin.setValue(weapon.multiple)
                        self.config_tab.weapon_parameters_section.sleep_divider_spin.setValue(weapon.sleep_divider)
                        self.config_tab.weapon_parameters_section.sleep_suber_spin.setValue(weapon.sleep_suber)

                    self.visualization_tab.update_weapon_visualization(weapon_name)

                    self.logger.debug(f"UI synchronized with GSI weapon: {weapon_name}")
                else:
                    self.logger.warning(f"GSI weapon not found in UI combo: {weapon_name}")

        except Exception as e:
            self.logger.error(f"GSI weapon sync error: {e}")
        finally:
            self._updating_from_gsi = False

    def _clear_ui_weapon_selection(self) -> None:
        """Clear weapon selection in UI when transitioning to automatic mode."""
        try:
            self._updating_from_gsi = True

            weapon_combo = self.config_tab.active_weapon_section.weapon_combo
            weapon_combo.setCurrentIndex(0)
            self.config_tab.weapon_parameters_section.multiple_spin.setValue(0)
            self.config_tab.weapon_parameters_section.sleep_divider_spin.setValue(1.0)
            self.config_tab.weapon_parameters_section.sleep_suber_spin.setValue(0.0)
            self.visualization_tab._clear_visualization()

            self.logger.debug("UI weapon selection cleared for automatic mode")

        except Exception as e:
            self.logger.error(f"UI weapon selection clearing error: {e}")
        finally:
            self._updating_from_gsi = False

    def _sync_weapon_ui(self, weapon_name: str) -> None:
        """Synchronize UI elements with weapon state (no signal loops)."""
        try:
            weapon_combo = self.config_tab.active_weapon_section.weapon_combo

            if not weapon_name:
                weapon_combo.setCurrentIndex(0)
                self.config_tab.weapon_parameters_section.multiple_spin.setValue(0)
                self.config_tab.weapon_parameters_section.sleep_divider_spin.setValue(1.0)
                self.config_tab.weapon_parameters_section.sleep_suber_spin.setValue(0.0)
                self.visualization_tab._clear_visualization()
                self.logger.debug("UI weapon selection cleared")
                return

            index = weapon_combo.findData(weapon_name)
            if index >= 0:
                weapon_combo.setCurrentIndex(index)

                # Update weapon parameters directly without triggering signals
                weapon = self.config_service.get_weapon_profile(weapon_name)
                if weapon:
                    self.config_tab.weapon_parameters_section.multiple_spin.setValue(weapon.multiple)
                    self.config_tab.weapon_parameters_section.sleep_divider_spin.setValue(weapon.sleep_divider)
                    self.config_tab.weapon_parameters_section.sleep_suber_spin.setValue(weapon.sleep_suber)

                self.visualization_tab.update_weapon_visualization(weapon_name)

                self.logger.debug(f"UI synchronized with weapon: {weapon_name}")
            else:
                self.logger.warning(f"Weapon not found in UI combo: {weapon_name}")

        except Exception as e:
            self.logger.error(f"UI synchronization error: {e}")

    def _on_status_changed_callback(self, status: Dict[str, Any]):
        """Thread-safe callback that emits signal to main Qt thread."""
        self.status_update_signal.emit(status)

    def _update_status(self, status: Dict[str, Any]):
        """Update RCS operational status display with GSI sync."""
        active = status.get('active', False)
        weapon_name = status.get('current_weapon', '')

        # RCS activation status - simplified: Active only when both active and weapon available
        if active and weapon_name:
            status_color = "#4CAF50"  # Green
            status_text = "Active"
        else:  # inactive OR no weapon = Inactive
            status_color = "#f44336"  # Red
            status_text = "Inactive"

        self.control_panel.status_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                border-radius: 6px;
            }}
        """)
        self.control_panel.status_text.setText(status_text)

        # Current weapon configuration avec synchronisation GSI
        if weapon_name:
            display_name = self.config_service.get_weapon_display_name(
                weapon_name)
            weapon_text = display_name

            # Synchronize UI with detected weapon
            self.sync_ui_with_gsi_weapon(weapon_name)
        else:
            weapon_text = "None"
            self._clear_ui_weapon_selection()

        self.control_panel.weapon_label.setText(
            f"Selected weapon: {weapon_text}")

        # Control button state management
        manual_activation_allowed = status.get('manual_activation_allowed', True)
        # Weapon validation will be handled in _start_compensation() with user feedback
        start_enabled = manual_activation_allowed and not active
        stop_enabled = active
        self._update_manual_controls_state(start_enabled, stop_enabled)

        self.gsi_status_update_signal.emit()

    def update_weapon_detection_status(self):
        """Update GSI subsystem status with granular information."""
        try:
            # GSI Connection Status Assessment
            if self.gsi_service:
                gsi_status = self.gsi_service.get_connection_status()
                connection_status = gsi_status.get("status", "Unknown")
                is_running = gsi_status.get("is_running", False)

                if connection_status == "Connected" and is_running:
                    gsi_color = "#4CAF50"  # Green
                    gsi_text = "GSI: Connected"
                elif connection_status == "Listening" and is_running:
                    gsi_color = "#FFC107"  # Yellow
                    gsi_text = "GSI: Listening"
                elif connection_status == "Error":
                    gsi_color = "#f44336"  # Red
                    gsi_text = "GSI: Error"
                else:
                    gsi_color = "#9e9e9e"  # Grey
                    gsi_text = "GSI: Disconnected"

                self.control_panel.gsi_indicator.setStyleSheet(f"""
                    QLabel {{
                        background-color: {gsi_color};
                        border-radius: 6px;
                    }}
                """)
                self.control_panel.gsi_text.setText(gsi_text)
            else:
                self.control_panel.gsi_indicator.setStyleSheet("""
                    QLabel {
                        background-color: #9e9e9e;
                        border-radius: 6px;
                    }
                """)
                self.control_panel.gsi_text.setText("GSI: Disabled")

            # Weapon Detection Status Assessment
            if self.weapon_detection_service:
                detection_status = self.weapon_detection_service.get_status()
                is_enabled = detection_status.get("enabled", False)

                if is_enabled:
                    detection_color = "#4CAF50"  # Green
                    detection_text = "Detection: Active"
                else:
                    detection_color = "#f44336"  # Red
                    detection_text = "Detection: Disabled"

                self.control_panel.detection_indicator.setStyleSheet(f"""
                    QLabel {{
                        background-color: {detection_color};
                        border-radius: 6px;
                    }}
                """)
                self.control_panel.detection_text.setText(detection_text)
            else:
                self.control_panel.detection_indicator.setStyleSheet("""
                    QLabel {
                        background-color: #9e9e9e;
                        border-radius: 6px;
                    }
                """)
                self.control_panel.detection_text.setText("Detection: Disabled")

        except Exception as e:
            self.logger.debug(f"GSI status update error: {e}")


    def _on_settings_saved(self):
        """Handle settings save event with dynamic reconfiguration."""
        features = self.config_service.config.get("features", {})
        tts_enabled = features.get("tts_enabled", True)
        self.recoil_service.configure_tts(tts_enabled)

        if self.auto_accept_service:
            auto_accept_enabled = features.get("auto_accept_enabled", False)
            if auto_accept_enabled:
                self.auto_accept_service.enable()
            else:
                self.auto_accept_service.disable()

        if self.follow_rcs_overlay:
            follow_rcs_enabled = features.get("follow_rcs_enabled", False)
            self.follow_rcs_overlay.set_active(follow_rcs_enabled)
            self.logger.debug(f"Follow RCS overlay {'enabled' if follow_rcs_enabled else 'disabled'}")

        if self.weapon_detection_service:
            gsi_config = self.config_service.config.get("gsi", {})
            self.weapon_detection_service.configure(gsi_config)

        # Refresh visualization if currently displayed
        if self.tabs.currentIndex() == 1:
            current_weapon = self.config_tab.get_selected_weapon()
            self.visualization_tab.update_weapon_visualization(current_weapon)

    def _on_hotkeys_updated(self):
        """Handle hotkeys update with hot reload capability."""
        try:
            if self.hotkey_service:
                self.logger.info("Performing hotkey configuration reload...")
                self.hotkey_service.reload_configuration()
                self.logger.info("Hotkey reload completed successfully")
            else:
                self.logger.warning(
                    "Hotkey service not available for reload operation")

        except Exception as e:
            self.logger.error(f"Hotkey reload operation failed: {e}")
            QMessageBox.warning(self, "Warning", f"Hotkey reload error: {e}")

    def _on_tab_changed(self, index: int):
        """Handle tab change event."""
        if index == 1:  # Visualization tab activated
            current_weapon = self.config_tab.get_selected_weapon()
            self.visualization_tab.update_weapon_visualization(current_weapon)

    def _update_manual_controls_state(self, start_enabled: bool, stop_enabled: bool):
        """Update the state of manual control buttons based on automatic detection status."""
        try:
            # Use the passed parameters to set button states directly
            auto_detection_active = bool(
                self.weapon_detection_service and
                self.weapon_detection_service.enabled
            )

            # Update auto detection button states
            self.control_panel.enable_detection_button.setEnabled(not auto_detection_active)
            self.control_panel.disable_detection_button.setEnabled(auto_detection_active)

            if auto_detection_active:
                self.control_panel.start_button.setEnabled(False)
                self.control_panel.stop_button.setEnabled(False)

                # Change tooltip text to indicate why controls are disabled
                self.control_panel.start_button.setToolTip(
                    "Manual RCS disabled - Automatic weapon detection is active")
                self.control_panel.stop_button.setToolTip(
                    "Manual RCS disabled - Automatic weapon detection is active")

                # Auto detection tooltips
                self.control_panel.enable_detection_button.setToolTip(
                    "Auto detection is already enabled")
                self.control_panel.disable_detection_button.setToolTip(
                    "Disable automatic weapon detection")
            else:
                # Normal controls when automatic detection is disabled
                self.control_panel.start_button.setEnabled(start_enabled)
                self.control_panel.stop_button.setEnabled(stop_enabled)

                # Re-enable weapon selection controls
                self.config_tab.set_weapon_controls_enabled(True)

                self.control_panel.start_button.setToolTip("Start manual recoil compensation")
                self.control_panel.stop_button.setToolTip("Stop manual recoil compensation")

                # Auto detection tooltips
                self.control_panel.enable_detection_button.setToolTip(
                    "Enable automatic weapon detection")
                self.control_panel.disable_detection_button.setToolTip(
                    "Auto detection is already disabled")

        except Exception as e:
            self.logger.error(f"Manual controls state update error: {e}")

    @Slot()
    def toggle_recoil_action_slot(self):
        """Slot to toggle recoil compensation."""
        try:
            if self.recoil_service.active:
                success = self.recoil_service.stop_compensation()
                if not success:
                    self.logger.error("Failed to stop compensation")
            else:
                current_weapon = self.recoil_service.current_weapon

                if not current_weapon:
                    self.logger.warning("No weapon available")
                    tts_service = getattr(self.recoil_service, 'tts_service', None)
                    if tts_service is not None:
                        tts_service.speak("No weapon available")
                    return

                success = self.recoil_service.start_compensation(
                    allow_manual_when_auto_enabled=False)

                if not success:
                    self.logger.error("Failed to start compensation")

            action_text = "started" if self.recoil_service.active else "stopped"
            self.logger.debug(f"Compensation {action_text} via hotkey")

        except Exception as e:
            self.logger.error(f"Toggle compensation error: {e}")



    @Slot(str)
    def weapon_select_action_slot(self, weapon_name: str):
        """Slot to select weapon via hotkey with conditional TTS announcement."""
        try:
            self.recoil_service.set_weapon(weapon_name)
            self._sync_weapon_ui(weapon_name)

            # Only announce if automatic weapon detection is not active
            should_announce = True
            if (self.weapon_detection_service and
                    self.weapon_detection_service.enabled):
                should_announce = False
                self.logger.debug(
                    "Weapon selection TTS suppressed: auto detection active")
                tts_service = getattr(self.recoil_service, 'tts_service', None)
                if tts_service is not None:
                    tts_service.speak("Manual weapon selection disabled")

            if should_announce:
                weapon_display = (self.config_service
                                    .get_weapon_display_name(weapon_name))
                if weapon_display is not None:
                    clean_name = weapon_display.replace(
                        "-", " ").replace("_", " ")
                    tts_service = getattr(self.recoil_service, 'tts_service', None)
                    if tts_service is not None:
                        tts_service.speak(clean_name)

            self.logger.debug(f"Weapon selected via hotkey: {weapon_name}")

        except Exception as e:
            self.logger.error(f"Weapon selection error: {e}")

    @Slot()
    def _handle_exit_request(self):
        """Handle exit request from hotkey (thread-safe via signal)."""
        self.close()

    def closeEvent(self, a0: Optional[QCloseEvent]):
        """Handle window close event with comprehensive cleanup."""
        try:
            if self.recoil_service.active:
                self.recoil_service.stop_compensation()

            if self.weapon_detection_service and self.weapon_detection_service.enabled:
                self.weapon_detection_service.disable()

            if self.gsi_service and self.gsi_service.is_running:
                self.gsi_service.stop_server()

            if self.bomb_timer_service:
                self.bomb_timer_service.stop()

            if hasattr(self, 'bomb_timer_overlay'):
                self.bomb_timer_overlay.close()

            # Unregister callbacks
            self.recoil_service.unregister_status_changed_callback(
                self._on_status_changed_callback)

            self.logger.info(
                "RCS System closed")

            if a0:
                a0.accept()

        except Exception as e:
            self.logger.error(f"Close event error: {e}")
            if a0:
                a0.accept()
