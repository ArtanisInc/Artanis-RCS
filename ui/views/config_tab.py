"""
Configuration tab for the user interface.
"""
import logging
from typing import Tuple, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.services.weapon_state_service import WeaponStateService

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QGroupBox, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.services.config_service import ConfigService


class ConfigSection:
    """Base configuration section with common styling."""

    @staticmethod
    def create_styled_label(text: str, bold: bool = False) -> QLabel:
        """Create consistently styled label."""
        label = QLabel(text)
        font = QFont("Arial", 10, QFont.Bold if bold else QFont.Normal)
        label.setFont(font)
        return label

    @staticmethod
    def create_styled_button(text: str, max_width: int = 150) -> QPushButton:
        """Create consistently styled button."""
        button = QPushButton(text)
        button.setMaximumHeight(32)
        button.setMaximumWidth(max_width)
        button.setFont(QFont("Arial", 10))
        return button


class GlobalWeaponSection(ConfigSection):
    """Global settings and weapon selection section."""

    def __init__(self):
        self.section = QGroupBox("Global Configuration and Weapon Selection")
        self.section.setMaximumHeight(140)
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self.section)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Global sensitivity
        sens_label = self.create_styled_label("Game Sensitivity:")
        self.global_sensitivity = QDoubleSpinBox()
        self._configure_sensitivity_spinner()

        # Weapon selection
        weapon_label = self.create_styled_label("Active Weapon:")
        self.weapon_combo = QComboBox()
        self._configure_weapon_combo()

        # Save button
        self.save_global_button = self.create_styled_button("Save")

        # Layout arrangement
        layout.addWidget(sens_label, 0, 0)
        layout.addWidget(self.global_sensitivity, 0, 1)
        layout.addWidget(self.save_global_button, 0, 2)
        layout.addWidget(weapon_label, 1, 0)
        layout.addWidget(self.weapon_combo, 1, 1, 1, 2)
        layout.setColumnStretch(3, 1)

    def _configure_sensitivity_spinner(self):
        """Configure sensitivity spinner properties."""
        self.global_sensitivity.setRange(0.1, 10.0)
        self.global_sensitivity.setSingleStep(0.1)
        self.global_sensitivity.setDecimals(2)
        self.global_sensitivity.setSuffix(" sens")
        self.global_sensitivity.setMaximumHeight(28)
        self.global_sensitivity.setMaximumWidth(100)
        self.global_sensitivity.setFont(QFont("Arial", 10))

    def _configure_weapon_combo(self):
        """Configure weapon combo box properties."""
        self.weapon_combo.setMaximumHeight(28)
        self.weapon_combo.setFont(QFont("Arial", 10))


class CompensationParamsSection(ConfigSection):
    """Compensation parameters section."""

    def __init__(self):
        self.section = QGroupBox("Compensation Parameters")
        self.section.setMaximumHeight(140)
        self.param_controls = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self.section)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Create controls
        self._create_param_controls()

        # Layout controls
        controls_layout = [
            ("Multiplier:", 'multiple', 0, 0),
            ("Delay Divider:", 'sleep_divider', 0, 2),
            ("Delay Adjustment:", 'sleep_suber', 1, 0)
        ]

        for label_text, key, row, col in controls_layout:
            label = self.create_styled_label(label_text)
            layout.addWidget(label, row, col)
            layout.addWidget(self.param_controls[key], row, col + 1)

        # Save button
        self.save_config_button = self.create_styled_button("Save")
        layout.addWidget(self.save_config_button, 1, 2, 1, 2)

    def _create_param_controls(self):
        """Create and configure parameter controls."""
        # Multiple control
        self.param_controls['multiple'] = QSpinBox()
        self.param_controls['multiple'].setRange(1, 20)
        self.param_controls['multiple'].setSuffix("x")
        self.param_controls['multiple'].setMaximumWidth(80)

        # Sleep divider control
        self.param_controls['sleep_divider'] = QDoubleSpinBox()
        self.param_controls['sleep_divider'].setRange(0.1, 20.0)
        self.param_controls['sleep_divider'].setSingleStep(0.1)
        self.param_controls['sleep_divider'].setSuffix(" div")
        self.param_controls['sleep_divider'].setMaximumWidth(100)

        # Sleep suber control
        self.param_controls['sleep_suber'] = QDoubleSpinBox()
        self.param_controls['sleep_suber'].setRange(-5.0, 5.0)
        self.param_controls['sleep_suber'].setSingleStep(0.1)
        self.param_controls['sleep_suber'].setSuffix(" ms")
        self.param_controls['sleep_suber'].setMaximumWidth(100)

        # Apply uniform styling
        for control in self.param_controls.values():
            control.setMaximumHeight(28)
            control.setFont(QFont("Arial", 10))


class FeaturesSection(ConfigSection):
    """Features configuration section."""

    def __init__(self):
        self.section = QGroupBox("Features")
        self.section.setMaximumHeight(100)  # Reduced height since we use 2 columns now
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self.section)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Audio feature checkbox
        self.audio_feature = QCheckBox("Audio Notification")
        self.audio_feature.setChecked(True)
        self.audio_feature.setFont(QFont("Arial", 10))

        # Bomb timer feature checkbox
        self.bomb_timer_feature = QCheckBox("Bomb Timer Overlay")
        self.bomb_timer_feature.setChecked(True)
        self.bomb_timer_feature.setFont(QFont("Arial", 10))

        # Auto Accept feature checkbox
        self.auto_accept_feature = QCheckBox("Auto Accept Matches")
        self.auto_accept_feature.setChecked(False)
        self.auto_accept_feature.setFont(QFont("Arial", 10))

        # Layout arrangement in two columns to optimize space
        # Column 1: Audio and Bomb Timer
        layout.addWidget(self.audio_feature, 0, 0)
        layout.addWidget(self.bomb_timer_feature, 1, 0)

        # Column 2: Auto Accept
        layout.addWidget(self.auto_accept_feature, 0, 1)

        # Set column stretches for better distribution
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)



class HotkeysSection(ConfigSection):
    """Hotkeys configuration section with System and Weapon sub-groups."""

    def __init__(self):
        self.section = QGroupBox("Keyboard Shortcuts")  # Main group box as before
        self.section.setMaximumHeight(320)
        self.hotkey_controls = {}
        self.key_options = self._get_key_options()
        self._setup_ui()

    def _get_key_options(self) -> List[str]:
        """Get available key options."""
        return (["INSERT", "HOME", "DELETE", "END", "PGUP", "PGDN", "XBUTTON1", "XBUTTON2"] +
                [f"F{i}" for i in range(1, 13)] +
                [f"NUMPAD{i}" for i in range(10)])

    def _setup_ui(self):
        main_layout = QVBoxLayout(self.section)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # System hotkeys sub-group
        self.system_group = QGroupBox("SYSTEM")
        self.system_group.setMaximumHeight(110)
        main_layout.addWidget(self.system_group)

        # Weapon hotkeys sub-group
        self.weapon_group = QGroupBox("WEAPONS")
        self.weapon_group.setMaximumHeight(130)
        main_layout.addWidget(self.weapon_group)

        # Setup each section
        self._setup_system_hotkeys()
        self._setup_weapon_hotkeys()

        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.save_hotkeys_button = self.create_styled_button("Save")
        self.save_hotkeys_button.setMinimumWidth(120)
        save_layout.addWidget(self.save_hotkeys_button)
        save_layout.addStretch()

        main_layout.addLayout(save_layout)

    def _setup_system_hotkeys(self):
        """Setup system hotkeys controls in their group box."""
        layout = QGridLayout(self.system_group)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Create system hotkey controls
        system_hotkeys = ['toggle_recoil', 'toggle_weapon_detection', 'exit']
        for hotkey in system_hotkeys:
            combo = QComboBox()
            combo.setMaximumHeight(26)
            combo.setMaximumWidth(100)
            combo.setFont(QFont("Arial", 10))
            for option in self.key_options:
                combo.addItem(option)
            self.hotkey_controls[hotkey] = combo

        # Layout system hotkeys
        hotkey_items = [
            ("Toggle RCS:", 'toggle_recoil', 0, 0),
            ("Toggle Detection:", 'toggle_weapon_detection', 0, 2),
            ("Exit Application:", 'exit', 1, 0)
        ]

        for label_text, key, row, col in hotkey_items:
            label = QLabel(label_text)
            label.setFont(QFont("Arial", 10))
            layout.addWidget(label, row, col)
            layout.addWidget(self.hotkey_controls[key], row, col + 1)

    def _setup_weapon_hotkeys(self):
        """Setup weapon hotkeys controls in their group box."""
        layout = QGridLayout(self.weapon_group)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Weapon selection
        weapon_label = self.create_styled_label("Weapon:")
        self.weapon_hotkey_combo = QComboBox()
        self.weapon_hotkey_combo.setObjectName("weapon_hotkey_combo")
        self.weapon_hotkey_combo.setMaximumHeight(26)
        self.weapon_hotkey_combo.setFont(QFont("Arial", 10))

        # Key selection
        key_label = self.create_styled_label("Key:")
        self.key_hotkey_combo = QComboBox()
        self.key_hotkey_combo.setObjectName("key_hotkey_combo")
        self.key_hotkey_combo.setMaximumHeight(26)
        self.key_hotkey_combo.setMaximumWidth(100)
        self.key_hotkey_combo.setFont(QFont("Arial", 10))

        # Add key options
        self.key_hotkey_combo.addItem("None", "")
        for option in self.key_options:
            self.key_hotkey_combo.addItem(option)

        # Action buttons
        self.assign_weapon_key_button = self._create_weapon_button("Assign")
        self.remove_weapon_key_button = self._create_weapon_button("Remove")

        # Layout weapon controls
        layout.addWidget(weapon_label, 0, 0)
        layout.addWidget(self.weapon_hotkey_combo, 0, 1)
        layout.addWidget(key_label, 0, 2)
        layout.addWidget(self.key_hotkey_combo, 0, 3)

        # Button layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.assign_weapon_key_button)
        buttons_layout.addWidget(self.remove_weapon_key_button)
        buttons_layout.addStretch()

        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        layout.addWidget(buttons_widget, 1, 0, 1, 4)

    def _create_weapon_hotkeys_section(self, layout):
        """Create weapon hotkeys controls."""
        # Section title
        weapon_title = QLabel("WEAPONS")
        weapon_title.setObjectName("section_title_header")
        weapon_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(weapon_title, 3, 0, 1, 4)

        # Weapon selection
        weapon_label = self.create_styled_label("Weapon:")
        self.weapon_hotkey_combo = QComboBox()
        self.weapon_hotkey_combo.setMaximumHeight(26)
        self.weapon_hotkey_combo.setFont(QFont("Arial", 10))

        # Key selection
        key_label = self.create_styled_label("Key:")
        self.key_hotkey_combo = QComboBox()
        self.key_hotkey_combo.setMaximumHeight(26)
        self.key_hotkey_combo.setMaximumWidth(100)
        self.key_hotkey_combo.setFont(QFont("Arial", 10))

        # Add key options
        self.key_hotkey_combo.addItem("None", "")
        for option in self.key_options:
            self.key_hotkey_combo.addItem(option)

        # Action buttons
        self.assign_weapon_key_button = self._create_weapon_button("Assign")
        self.remove_weapon_key_button = self._create_weapon_button("Remove")

        # Layout weapon controls
        layout.addWidget(weapon_label, 4, 0)
        layout.addWidget(self.weapon_hotkey_combo, 4, 1)
        layout.addWidget(key_label, 4, 2)
        layout.addWidget(self.key_hotkey_combo, 4, 3)

        # Button layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.assign_weapon_key_button)
        buttons_layout.addWidget(self.remove_weapon_key_button)
        buttons_layout.addStretch()

        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        layout.addWidget(buttons_widget, 5, 0, 1, 4)

    def _create_weapon_button(self, text: str) -> QPushButton:
        """Create weapon action button."""
        button = QPushButton(text)
        button.setMaximumHeight(28)
        button.setMaximumWidth(80 if text == "Assign" else 90)
        button.setFont(QFont("Arial", 9))
        return button


class ConfigTab(QWidget):
    """Configuration tab with modular architecture."""

    weapon_changed = pyqtSignal(str)
    settings_saved = pyqtSignal()
    hotkeys_updated = pyqtSignal()

    def __init__(self, config_service: ConfigService, weapon_state_service: Optional['WeaponStateService'] = None):
        super().__init__()
        self.logger = logging.getLogger("ConfigTab")
        self.config_service = config_service
        self.weapon_state_service = weapon_state_service

        # Create sections
        self.global_weapon_section = GlobalWeaponSection()
        self.params_section = CompensationParamsSection()
        self.features_section = FeaturesSection()
        self.hotkeys_section = HotkeysSection()

        self._setup_ui()
        self._setup_connections()
        self._load_data()
        self.logger.debug("Configuration tab initialized")

    def _setup_ui(self):
        """Setup main UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        main_layout.addWidget(self.global_weapon_section.section)
        main_layout.addWidget(self.params_section.section)
        main_layout.addWidget(self.features_section.section)
        main_layout.addWidget(self.hotkeys_section.section)

    def _setup_connections(self):
        """Setup signal connections."""
        # Main controls
        self.global_weapon_section.weapon_combo.currentIndexChanged.connect(
            self._on_weapon_changed)

        # Save buttons
        self.global_weapon_section.save_global_button.clicked.connect(
            self._save_global_config)
        self.params_section.save_config_button.clicked.connect(
            self._save_weapon_config)
        self.hotkeys_section.save_hotkeys_button.clicked.connect(
            self._save_hotkeys_config)

        # Features auto-save (no save button)
        self.features_section.audio_feature.toggled.connect(
            self._save_features_config)
        self.features_section.bomb_timer_feature.toggled.connect(
            self._save_features_config)
        self.features_section.auto_accept_feature.toggled.connect(
            self._save_features_config)

        # Weapon hotkeys
        self.hotkeys_section.weapon_hotkey_combo.currentIndexChanged.connect(
            self._on_weapon_hotkey_changed)
        self.hotkeys_section.assign_weapon_key_button.clicked.connect(
            self._assign_weapon_key)
        self.hotkeys_section.remove_weapon_key_button.clicked.connect(
            self._remove_weapon_key)

    def _load_data(self):
        """Load data from configuration service."""
        try:
            self._load_global_settings()
            self._load_weapons()
            self._load_features_settings()
            self._load_hotkeys()
        except Exception as e:
            self.logger.error("Data loading failed: %s", e)
            QMessageBox.warning(self, "Warning", f"Data loading error: {e}")

    def _load_global_settings(self):
        """Load global settings."""
        sensitivity = self.config_service.config.get("game_sensitivity", 1.0)
        self.global_weapon_section.global_sensitivity.setValue(sensitivity)

    def _load_weapons(self):
        """Load weapons into combo boxes."""
        # Store current selections
        current_weapon = self.global_weapon_section.weapon_combo.currentData()

        # Clear and repopulate
        self.global_weapon_section.weapon_combo.clear()
        self.hotkeys_section.weapon_hotkey_combo.clear()

        self.global_weapon_section.weapon_combo.addItem(
            "Select a weapon...", "")
        self.hotkeys_section.weapon_hotkey_combo.addItem(
            "Select a weapon...", "")

        for name in self.config_service.weapon_profiles.keys():
            display_name = self.config_service.get_weapon_display_name(name)
            self.global_weapon_section.weapon_combo.addItem(display_name, name)
            self.hotkeys_section.weapon_hotkey_combo.addItem(
                display_name, name)

        # Restore selection
        if current_weapon:
            index = self.global_weapon_section.weapon_combo.findData(
                current_weapon)
            if index >= 0:
                self.global_weapon_section.weapon_combo.setCurrentIndex(index)

        # Important: éviter l'appel automatique lors du chargement initial
        current_index = self.global_weapon_section.weapon_combo.currentIndex()
        if current_index > 0:  # Seulement si une arme valide est sélectionnée
            self._on_weapon_changed(current_index)

    def _load_features_settings(self):
        """Load features settings."""
        features = self.config_service.config.get("features", {})

        self.features_section.audio_feature.setChecked(
            features.get("tts_enabled", True))

        self.features_section.bomb_timer_feature.setChecked(
            features.get("bomb_timer_enabled", True))

        self.features_section.auto_accept_feature.setChecked(
            features.get("auto_accept_enabled", False))

    def _load_hotkeys(self):
        """Load hotkeys configuration."""
        hotkeys = self.config_service.hotkeys

        for key, control in self.hotkeys_section.hotkey_controls.items():
            value = hotkeys.get(key)
            if value:
                index = control.findText(value)
                if index >= 0:
                    control.setCurrentIndex(index)

    def _on_weapon_changed(self, index):
        """Handle weapon selection change event."""
        if index < 0:
            return

        # Check if we should process this UI change
        if self.weapon_state_service and not self.weapon_state_service.should_process_ui_change():
            self.logger.debug("Skipping UI weapon change during GSI update")
            return

        weapon_name = self.global_weapon_section.weapon_combo.currentData()

        # Handle weapon deselection ("Select a weapon..." option)
        if not weapon_name:
            # Clear weapon parameters display
            self.params_section.param_controls['multiple'].setValue(0)
            self.params_section.param_controls['sleep_divider'].setValue(1.0)
            self.params_section.param_controls['sleep_suber'].setValue(0.0)

            # Emit signal with empty weapon name to clear selection
            self.weapon_changed.emit("")
            return

        weapon = self.config_service.get_weapon_profile(weapon_name)
        if not weapon:
            self.logger.warning("Weapon profile not found: %s", weapon_name)
            return

        # Update controls
        self.params_section.param_controls['multiple'].setValue(
            weapon.multiple)
        self.params_section.param_controls['sleep_divider'].setValue(
            weapon.sleep_divider)
        self.params_section.param_controls['sleep_suber'].setValue(
            weapon.sleep_suber)

        self.weapon_changed.emit(weapon_name)

    def _on_weapon_hotkey_changed(self, index):
        """Handle weapon hotkey selection change."""
        if index < 0:
            return

        weapon_name = self.hotkeys_section.weapon_hotkey_combo.currentData()
        if not weapon_name:
            self.hotkeys_section.key_hotkey_combo.setCurrentIndex(0)
            return

        # Find assigned key for this weapon
        assigned_key = self.config_service.hotkeys.get(weapon_name, "")

        if assigned_key:
            index = self.hotkeys_section.key_hotkey_combo.findText(
                assigned_key)
            self.hotkeys_section.key_hotkey_combo.setCurrentIndex(
                index if index >= 0 else 0)
        else:
            self.hotkeys_section.key_hotkey_combo.setCurrentIndex(0)

    def _assign_weapon_key(self):
        """Assign key to selected weapon."""
        try:
            weapon_name = self.hotkeys_section.weapon_hotkey_combo.currentData()
            if not weapon_name:
                QMessageBox.warning(self, "Warning", "Please select a weapon")
                return

            key_text = self.hotkeys_section.key_hotkey_combo.currentText()
            if not key_text or key_text == "None":
                QMessageBox.warning(self, "Warning", "Please select a key")
                return

            # Assign key
            self.config_service.hotkeys[weapon_name] = key_text

            weapon_display = self.config_service.get_weapon_display_name(
                weapon_name)
            QMessageBox.information(
                self, "Success", f"Key {key_text} assigned to {weapon_display}")

        except Exception as e:
            self.logger.error("Key assignment failed: %s", e)
            QMessageBox.critical(self, "Error", f"Assignment error: {e}")

    def _remove_weapon_key(self):
        """Remove key assignment for selected weapon."""
        try:
            weapon_name = self.hotkeys_section.weapon_hotkey_combo.currentData()
            if not weapon_name:
                QMessageBox.warning(self, "Warning", "Please select a weapon")
                return

            if weapon_name in self.config_service.hotkeys:
                del self.config_service.hotkeys[weapon_name]
                self.hotkeys_section.key_hotkey_combo.setCurrentIndex(0)

                weapon_display = self.config_service.get_weapon_display_name(
                    weapon_name)
                QMessageBox.information(
                    self, "Success", f"Assignment removed for {weapon_display}")
            else:
                QMessageBox.information(self, "Info",
                                        "No key assigned to this weapon")

        except Exception as e:
            self.logger.error("Key removal failed: %s", e)
            QMessageBox.critical(self, "Error", f"Removal error: {e}")

    def _validate_hotkeys_conflicts(self) -> Tuple[bool, List[str]]:
        """Validate hotkeys for conflicts."""
        try:
            conflicts = []
            hotkey_usage = {}

            # System hotkeys
            system_hotkeys = {
                'toggle_recoil': 'Toggle compensation',
                'toggle_weapon_detection': 'Weapon detection',
                'exit': 'Exit application'
            }

            for hotkey_key, description in system_hotkeys.items():
                if hotkey_key in self.hotkeys_section.hotkey_controls:
                    selected_key = (
                        self.hotkeys_section.hotkey_controls[hotkey_key] .currentText())
                    if selected_key and selected_key.strip():
                        if selected_key not in hotkey_usage:
                            hotkey_usage[selected_key] = []
                        hotkey_usage[selected_key].append(
                            f"System: {description}")

            # Weapon hotkeys
            for weapon_name, assigned_key in self.config_service.hotkeys.items():
                if weapon_name in self.config_service.weapon_profiles and assigned_key:
                    weapon_display = self.config_service.get_weapon_display_name(
                        weapon_name)
                    if assigned_key not in hotkey_usage:
                        hotkey_usage[assigned_key] = []
                    hotkey_usage[assigned_key].append(
                        f"Weapon: {weapon_display}")

            # Detect conflicts
            for key, actions in hotkey_usage.items():
                if len(actions) > 1:
                    actions_str = " | ".join(actions)
                    conflicts.append(f"Key '{key}' assigned to: {actions_str}")

            return len(conflicts) == 0, conflicts

        except Exception as e:
            self.logger.error("Hotkey validation failed: %s", e)
            return False, [f"Validation error: {e}"]

    def _save_global_config(self):
        """Save global configuration."""
        try:
            new_sensitivity = self.global_weapon_section.global_sensitivity.value()
            current_sensitivity = self.config_service.config.get(
                "game_sensitivity", 1.0)

            # Check if sensitivity changed
            if abs(new_sensitivity - current_sensitivity) > 0.001:
                success = self.config_service.update_global_sensitivity(
                    new_sensitivity)
                if not success:
                    QMessageBox.warning(
                        self, "Warning", "Sensitivity update failed")
                    return
            else:
                self.config_service.config["game_sensitivity"] = new_sensitivity

            success = self.config_service.save_config()

            if success:
                QMessageBox.information(
                    self, "Success", "Global configuration saved")
                self.settings_saved.emit()
            else:
                QMessageBox.warning(self, "Warning", "Save failed")

        except Exception as e:
            self.logger.error("Global config save failed: %s", e)
            QMessageBox.critical(self, "Error", f"Save error: {e}")

    def _save_weapon_config(self):
        """Save weapon configuration."""
        try:
            weapon_name = self.global_weapon_section.weapon_combo.currentData()
            if not weapon_name:
                QMessageBox.warning(self, "Warning", "No weapon selected")
                return

            weapon = self.config_service.get_weapon_profile(weapon_name)
            if not weapon:
                return

            new_sensitivity = self.global_weapon_section.global_sensitivity.value()
            sensitivity_changed = abs(
                weapon.game_sensitivity -
                new_sensitivity) > 0.001

            # Update parameters
            weapon.multiple = self.params_section.param_controls['multiple'].value(
            )
            weapon.sleep_divider = (
                self.params_section.param_controls['sleep_divider'] .value())
            weapon.sleep_suber = (
                self.params_section.param_controls['sleep_suber'] .value())

            # Update sensitivity if needed
            if sensitivity_changed:
                success = self.config_service.update_weapon_sensitivity(
                    weapon_name, new_sensitivity)
                if not success:
                    QMessageBox.warning(
                        self, "Warning", "Sensitivity update failed")
                    return
            else:
                weapon.recalculate_pattern()

            success = self.config_service.save_weapon_profile(weapon)

            if success:
                QMessageBox.information(
                    self, "Success", "Weapon configuration saved")
                self.settings_saved.emit()
            else:
                QMessageBox.warning(self, "Warning", "Save failed")

        except Exception as e:
            self.logger.error("Weapon config save failed: %s", e)
            QMessageBox.critical(self, "Error", f"Save error: {e}")

    def _save_features_config(self):
        """Save features configuration."""
        try:
            # Save all features settings in one place
            features_settings = {
                "tts_enabled": self.features_section.audio_feature.isChecked(),
                "bomb_timer_enabled": self.features_section.bomb_timer_feature.isChecked(),
                "auto_accept_enabled": self.features_section.auto_accept_feature.isChecked()
            }
            self.config_service.config["features"] = features_settings

            # Save configuration
            success = self.config_service.save_config()

            if success:
                # Emit signal to notify about the change
                self.settings_saved.emit()
                self.logger.debug("Features configuration saved")
            else:
                self.logger.warning("Failed to save features configuration")

        except Exception as e:
            self.logger.error("Features config save failed: %s", e)

    def _save_hotkeys_config(self):
        """Save hotkeys configuration with conflict validation."""
        try:
            # Validate for conflicts
            is_valid, conflicts = self._validate_hotkeys_conflicts()

            if not is_valid:
                conflict_details = "\n".join(
                    [f"• {conflict}" for conflict in conflicts])
                error_message = (
                    "HOTKEY CONFLICT DETECTED\n\n"
                    "Multiple actions share the same key:\n\n"
                    f"{conflict_details}\n\n"
                    "❌ Save cancelled.\n"
                    "✅ Please fix conflicts before saving."
                )
                QMessageBox.warning(self, "Hotkey Conflict", error_message)
                return

            # Save if valid
            hotkeys = {}

            # System hotkeys
            for key, control in self.hotkeys_section.hotkey_controls.items():
                selected_key = control.currentText()
                if selected_key and selected_key.strip():
                    hotkeys[key] = selected_key

            # Preserve existing weapon hotkeys
            for weapon_name in self.config_service.weapon_profiles.keys():
                if weapon_name in self.config_service.hotkeys:
                    hotkeys[weapon_name] = self.config_service.hotkeys[weapon_name]

            success = self.config_service.save_hotkeys(hotkeys)

            if success:
                QMessageBox.information(
                    self, "Success", "Hotkeys configuration saved successfully")
                self.settings_saved.emit()
                self.hotkeys_updated.emit()
            else:
                QMessageBox.warning(self, "Warning", "Save failed")

        except Exception as e:
            self.logger.error("Hotkeys save failed: %s", e)
            QMessageBox.critical(self, "Error", f"Save error: {e}")

    def get_selected_weapon(self) -> str:
        """Get currently selected weapon name."""
        index = self.global_weapon_section.weapon_combo.currentIndex()
        if index < 0:
            return ""
        return self.global_weapon_section.weapon_combo.currentData() or ""

    def set_weapon_controls_enabled(self, enabled: bool):
        """Enable/disable weapon selection controls based on automatic detection status."""
        try:
            self.global_weapon_section.weapon_combo.setEnabled(enabled)

            if not enabled:
                self.global_weapon_section.weapon_combo.setToolTip(
                    "Weapon selection disabled - Automatic weapon detection is active")
            else:
                self.global_weapon_section.weapon_combo.setToolTip(
                    "Select the active weapon for recoil compensation")

        except Exception as e:
            self.logger.error("Weapon controls state update error: %s", e)
