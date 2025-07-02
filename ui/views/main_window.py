"""
Main application window with modular architecture.
"""
import logging
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QTabWidget,
    QGroupBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCloseEvent, QFont

from core.services.recoil_service import RecoilService
from core.services.config_service import ConfigService
from ui.views.config_tab import ConfigTab
from ui.views.visualization_tab import VisualizationTab
from ui.views.styles import MAIN_WINDOW_STYLES
from ui.widgets.bomb_timer_overlay import BombTimerOverlay


class ControlPanel:
    """Control panel for main system operations."""

    def __init__(self):
        self.group_box = QGroupBox("System Control")
        self._setup_ui()

    def _setup_ui(self):
        """Setup control panel UI with three distinct sections."""
        layout = QHBoxLayout(self.group_box)
        layout.setSpacing(10)

        # RCS Status section
        status_frame = self._create_status_section()
        layout.addWidget(status_frame)

        # Controls section
        controls_frame = self._create_controls_section()
        layout.addWidget(controls_frame)

        # GSI Status section
        gsi_frame = self._create_gsi_status_section()
        layout.addWidget(gsi_frame)

        # Equal distribution
        layout.setStretchFactor(status_frame, 1)
        layout.setStretchFactor(controls_frame, 1)
        layout.setStretchFactor(gsi_frame, 1)

    def _create_status_section(self) -> QFrame:
        """Create RCS status display section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)

        title = QLabel("RCS Status")
        title.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(title)

        self.status_label = QLabel("🔴 Inactive")
        self.weapon_label = QLabel("Selected weapon: None")

        for label in [self.status_label, self.weapon_label]:
            label.setFont(QFont("Arial", 9))
            label.setMinimumHeight(18)
            layout.addWidget(label)

        layout.addStretch()
        return frame

    def _create_controls_section(self) -> QFrame:
        """Create control buttons section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)

        title = QLabel("Actions")
        title.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(title)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

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

    def _create_gsi_status_section(self) -> QFrame:
        """Create dedicated GSI status display section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)

        title = QLabel("GSI Status")
        title.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(title)

        # Separated GSI status indicators
        self.gsi_connection_label = QLabel("⚪ GSI: Disabled")
        self.weapon_detection_label = QLabel("⚪ Detection: Disabled")

        for label in [self.gsi_connection_label, self.weapon_detection_label]:
            label.setFont(QFont("Arial", 9))
            label.setMinimumHeight(18)
            layout.addWidget(label)

        layout.addStretch()
        return frame

    def _create_action_button(
            self,
            text: str,
            bg_color: str,
            hover_color: str) -> QPushButton:
        """Create styled action button."""
        button = QPushButton(text)
        button.setMinimumHeight(30)
        button.setFont(QFont("Arial", 9, QFont.Bold))

        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
        """)

        return button


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(
            self,
            recoil_service: RecoilService,
            config_service: ConfigService):
        super().__init__()

        self.logger = logging.getLogger("MainWindow")
        self.recoil_service = recoil_service
        self.config_service = config_service

        # Service references
        self.hotkey_service = None
        self.gsi_service = None
        self.weapon_detection_service = None
        self.bomb_timer_service = None

        # UI components
        self.control_panel = ControlPanel()

        # Bomb timer overlay
        self.bomb_timer_overlay = BombTimerOverlay()

        # Periodic GSI status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_gsi_status)
        self.status_timer.start(1000)  # 1Hz update frequency

        self._setup_ui()
        self._setup_connections()
        self._apply_styles()

        # Register status callback with recoil service
        self.recoil_service.register_status_changed_callback(
            self._update_status)

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

        # Immediate status refresh
        self._update_gsi_status()

        # Update UI to reflect initial weapon detection state
        self._sync_initial_ui_state()

    def set_bomb_timer_service(self, bomb_timer_service):
        """Set bomb timer service and connect overlay."""
        self.bomb_timer_service = bomb_timer_service

        # Connect bomb timer service to overlay
        bomb_timer_service.set_timer_update_callback(
            self.bomb_timer_overlay.update_bomb_state
        )

        self.logger.debug("Bomb timer service connected to overlay")

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
        """Setup main UI layout with restored interface."""
        self.setWindowTitle("Artanis's RCS")
        # Set window flags to show title bar with close and minimize buttons
        flags = (Qt.Window | Qt.WindowTitleHint |  # type: ignore
                Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)  # type: ignore
        self.setWindowFlags(flags)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Control panel with three sections
        main_layout.addWidget(self.control_panel.group_box)

        # UI separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Tab widget for configuration and visualization
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)

        self.config_tab = ConfigTab(self.config_service)
        self.visualization_tab = VisualizationTab(self.config_service)

        self.tabs.addTab(self.config_tab, "⚙️ Configuration")
        self.tabs.addTab(self.visualization_tab, "📊 Visualization")

        main_layout.addWidget(self.tabs)

        # Fixed window dimensions
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def _setup_connections(self):
        """Setup signal-slot connections."""
        # Control panel connections
        self.control_panel.start_button.clicked.connect(
            self._start_compensation)
        self.control_panel.stop_button.clicked.connect(self._stop_compensation)

        # Configuration tab connections
        self.config_tab.weapon_changed.connect(self._on_weapon_changed)
        self.config_tab.settings_saved.connect(self._on_settings_saved)
        self.config_tab.hotkeys_updated.connect(self._on_hotkeys_updated)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _apply_styles(self):
        """Apply application stylesheet."""
        self.setStyleSheet(MAIN_WINDOW_STYLES)

    def _start_compensation(self):
        """Start recoil compensation with validation and error handling."""
        try:
            weapon_name = self.config_tab.get_selected_weapon()
            if not weapon_name:
                QMessageBox.warning(self, "Warning", "Please select a weapon")
                return

            # Update weapon configuration if changed
            if self.recoil_service.current_weapon != weapon_name:
                self.recoil_service.set_weapon(weapon_name)

            success = self.recoil_service.start_compensation()

            if success:
                self.control_panel.start_button.setEnabled(False)
                self.control_panel.stop_button.setEnabled(True)
                self.logger.debug(
                    f"Compensation started for weapon: {weapon_name}")
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

    def sync_ui_with_gsi_weapon(self, weapon_name: str) -> None:
        """Synchronize UI weapon selection with GSI detected weapon."""
        try:
            if not weapon_name:
                return

            weapon_combo = self.config_tab.global_weapon_section.weapon_combo
            index = weapon_combo.findData(weapon_name)

            if index >= 0:
                # Bloquer temporairement les signaux pour éviter la récursion
                weapon_combo.blockSignals(True)
                weapon_combo.setCurrentIndex(index)
                weapon_combo.blockSignals(False)

                # Mettre à jour la visualisation
                self.visualization_tab.update_weapon_visualization(weapon_name)

                self.logger.debug(
                    f"UI synchronized with GSI weapon: {weapon_name}")
            else:
                self.logger.warning(
                    f"GSI weapon not found in UI combo: {weapon_name}")

        except Exception as e:
            self.logger.error(f"UI synchronization error: {e}")

    def _clear_ui_weapon_selection(self) -> None:
        """Clear weapon selection in UI when transitioning to automatic mode."""
        try:
            weapon_combo = self.config_tab.global_weapon_section.weapon_combo

            # Block signals to prevent recursion
            weapon_combo.blockSignals(True)
            weapon_combo.setCurrentIndex(0)  # Set to "Select a weapon..." instead of empty
            weapon_combo.blockSignals(False)

            # Clear visualization
            self.visualization_tab._clear_visualization()

            self.logger.debug("UI weapon selection cleared for automatic mode")

        except Exception as e:
            self.logger.error(f"UI weapon selection clearing error: {e}")

    def _update_status(self, status: Dict[str, Any]):
        """Update RCS operational status display with GSI sync."""
        # Get status information
        active = status.get('active', False)
        weapon_name = status.get('current_weapon', '')

        # RCS activation status - simplified: Active only when both active and weapon available
        if active and weapon_name:
            status_icon = "🟢"
            status_text = "Active"
        else:  # inactive OR no weapon = Inactive
            status_icon = "🔴"
            status_text = "Inactive"

        self.control_panel.status_label.setText(f"{status_icon} {status_text}")

        # Current weapon configuration avec synchronisation GSI
        if weapon_name:
            display_name = self.config_service.get_weapon_display_name(
                weapon_name)
            weapon_text = display_name

            # Synchroniser l'interface utilisateur avec l'arme détectée
            self.sync_ui_with_gsi_weapon(weapon_name)
        else:
            weapon_text = "None"
            # Clear UI weapon selection when no weapon is set
            self._clear_ui_weapon_selection()

        self.control_panel.weapon_label.setText(
            f"Selected weapon: {weapon_text}")

        # Control button state management
        manual_activation_allowed = status.get('manual_activation_allowed', True)
        # Enable start button when manual activation allowed and not active
        # Weapon validation will be handled in _start_compensation() with user feedback
        start_enabled = manual_activation_allowed and not active
        stop_enabled = active
        self._update_manual_controls_state(start_enabled, stop_enabled)

    def _update_gsi_status(self):
        """Update GSI subsystem status with granular information."""
        try:
            # GSI Connection Status Assessment
            if self.gsi_service:
                gsi_status = self.gsi_service.get_connection_status()
                connection_status = gsi_status.get("status", "Unknown")
                is_running = gsi_status.get("is_running", False)

                if connection_status == "Connected" and is_running:
                    gsi_icon = "🟢"
                    gsi_text = "Connected"
                elif connection_status == "Listening" and is_running:
                    gsi_icon = "🟡"
                    gsi_text = "Listening"
                elif connection_status == "Error":
                    gsi_icon = "🔴"
                    gsi_text = "Error"
                else:
                    gsi_icon = "⚪"
                    gsi_text = "Disconnected"

                self.control_panel.gsi_connection_label.setText(
                    f"{gsi_icon} GSI: {gsi_text}")
            else:
                self.control_panel.gsi_connection_label.setText(
                    "⚪ GSI: Disabled")

            # Weapon Detection Status Assessment
            if self.weapon_detection_service:
                detection_status = self.weapon_detection_service.get_status()
                is_enabled = detection_status.get("enabled", False)
                current_state = detection_status.get("current_state", {})
                current_weapon = current_state.get("weapon")

                if is_enabled:
                    if current_weapon:
                        detection_icon = "🟢"
                        detection_text = f"Active ({current_weapon})"
                    else:
                        detection_icon = "🟡"
                        detection_text = "Active (No weapon)"
                else:
                    detection_icon = "🔴"
                    detection_text = "Disabled"

                self.control_panel.weapon_detection_label.setText(
                    f"{detection_icon} Detection: {detection_text}")
            else:
                self.control_panel.weapon_detection_label.setText(
                    "⚪ Detection: Disabled")

        except Exception as e:
            self.logger.debug(f"GSI status update error: {e}")

    def _on_weapon_changed(self, weapon_name: str):
        """Handle weapon selection change event."""
        # Handle weapon deselection
        # Update visualization tab (handle deselection)
        if not weapon_name:
            self.visualization_tab.update_weapon_visualization(None)
            # Clear weapon in recoil service
            if self.recoil_service.current_weapon is not None:
                self.recoil_service.set_weapon("")
        else:
            self.visualization_tab.update_weapon_visualization(weapon_name)
            # Update recoil service configuration
            if self.recoil_service.current_weapon != weapon_name:
                self.recoil_service.set_weapon(weapon_name)

    def _on_settings_saved(self):
        """Handle settings save event with dynamic reconfiguration."""
        # Update TTS configuration dynamically
        features = self.config_service.config.get("features", {})
        tts_enabled = features.get("tts_enabled", True)
        self.recoil_service.configure_tts(tts_enabled)

        # Update GSI configuration if service available
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
            auto_detection_active = (
                self.weapon_detection_service and
                self.weapon_detection_service.enabled
            )

            if auto_detection_active:
                # Désactiver les contrôles manuels si la détection automatique est active
                self.control_panel.start_button.setEnabled(False)
                self.control_panel.stop_button.setEnabled(False)

                # Optionnel: changer le texte pour indiquer pourquoi c'est désactivé
                self.control_panel.start_button.setToolTip(
                    "Manual control disabled - Automatic weapon detection is active")
                self.control_panel.stop_button.setToolTip(
                    "Manual control disabled - Automatic weapon detection is active")
            else:
                # Contrôles normaux quand la détection automatique est désactivée
                self.control_panel.start_button.setEnabled(start_enabled)
                self.control_panel.stop_button.setEnabled(stop_enabled)

                # Réactiver les contrôles de sélection d'arme
                self.config_tab.set_weapon_controls_enabled(True)

                # Remettre les tooltips normaux
                self.control_panel.start_button.setToolTip("Start recoil compensation")
                self.control_panel.stop_button.setToolTip("Stop recoil compensation")

        except Exception as e:
            self.logger.error(f"Manual controls state update error: {e}")

    def closeEvent(self, a0: Optional[QCloseEvent]):
        """Handle window close event with comprehensive cleanup."""
        try:
            # Stop periodic timers
            if hasattr(self, 'status_timer'):
                self.status_timer.stop()

            # Stop active compensation
            if self.recoil_service.active:
                self.recoil_service.stop_compensation()

            # GSI services cleanup
            if self.weapon_detection_service and self.weapon_detection_service.enabled:
                self.weapon_detection_service.disable()

            if self.gsi_service and self.gsi_service.is_running:
                self.gsi_service.stop_server()

            # Bomb timer cleanup
            if self.bomb_timer_service:
                self.bomb_timer_service.stop()

            if hasattr(self, 'bomb_timer_overlay'):
                self.bomb_timer_overlay.close()

            # Unregister callbacks
            self.recoil_service.unregister_status_changed_callback(
                self._update_status)

            self.logger.info(
                "Main window closed with resource cleanup")

            if a0:
                a0.accept()

        except Exception as e:
            self.logger.error(f"Close event error: {e}")
            if a0:
                a0.accept()
