"""
Configuration tab for the user interface.
"""
import logging
from typing import Tuple, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QGroupBox, QCheckBox, QMessageBox, QFrame, QSlider, QColorDialog
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QColor

from core.services.config_service import ConfigService


class ConfigSection:
    """Base configuration section with common styling."""

    @staticmethod
    def create_styled_label(text: str, bold: bool = False) -> QLabel:
        """Create consistently styled label."""
        label = QLabel(text)
        font = QFont("Arial", 10)
        font.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
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


class ActiveWeaponSection(ConfigSection):
    """Active weapon selection for recoil control."""

    def __init__(self):
        self.section = QGroupBox("Active Weapon Selection")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self.section)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        weapon_label = self.create_styled_label("Current Active Weapon:")
        weapon_label.setMinimumWidth(140)
        self.weapon_combo = QComboBox()
        self._configure_weapon_combo()

        layout.addWidget(weapon_label)
        layout.addWidget(self.weapon_combo)
        layout.addStretch()

    def _configure_weapon_combo(self):
        """Configure weapon combo box properties."""
        self.weapon_combo.setMaximumHeight(28)
        self.weapon_combo.setMinimumWidth(200)
        self.weapon_combo.setFont(QFont("Arial", 10))


class WeaponParametersSection(ConfigSection):
    """Weapon parameters configuration section."""

    def __init__(self):
        self.section = QGroupBox("Weapon Parameters")
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self.section)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # Info text
        info_label = QLabel("Select a weapon above to configure its parameters:")
        info_label.setFont(QFont("Arial", 9))
        info_label.setStyleSheet("color: #666;")
        main_layout.addWidget(info_label)

        # Settings in a grid for better alignment
        settings_grid = QGridLayout()
        settings_grid.setSpacing(10)
        settings_grid.setColumnMinimumWidth(0, 140)
        settings_grid.setColumnMinimumWidth(2, 140)

        # Row 0 - Sensitivity and Multiplier
        sens_label = self.create_styled_label("Game Sensitivity:")
        self.global_sensitivity = QDoubleSpinBox()
        self._configure_sensitivity_spinner()
        settings_grid.addWidget(sens_label, 0, 0)
        settings_grid.addWidget(self.global_sensitivity, 0, 1)

        mult_label = self.create_styled_label("Multiplier:")
        self.multiple_spin = QSpinBox()
        self._configure_multiplier_spinner()
        settings_grid.addWidget(mult_label, 0, 2)
        settings_grid.addWidget(self.multiple_spin, 0, 3)

        # Row 1 - Delay Divider and Delay Adjustment
        div_label = self.create_styled_label("Delay Divider:")
        self.sleep_divider_spin = QDoubleSpinBox()
        self._configure_sleep_divider_spinner()
        settings_grid.addWidget(div_label, 1, 0)
        settings_grid.addWidget(self.sleep_divider_spin, 1, 1)

        suber_label = self.create_styled_label("Delay Adjustment:")
        self.sleep_suber_spin = QDoubleSpinBox()
        self._configure_sleep_suber_spinner()
        settings_grid.addWidget(suber_label, 1, 2)
        settings_grid.addWidget(self.sleep_suber_spin, 1, 3)

        # Row 2 - Jitter Timing and Jitter Movement
        jitter_timing_label = self.create_styled_label("Jitter Timing:")
        self.jitter_timing_spin = QDoubleSpinBox()
        self._configure_jitter_timing_spinner()
        settings_grid.addWidget(jitter_timing_label, 2, 0)
        settings_grid.addWidget(self.jitter_timing_spin, 2, 1)

        jitter_movement_label = self.create_styled_label("Jitter Movement:")
        self.jitter_movement_spin = QDoubleSpinBox()
        self._configure_jitter_movement_spinner()
        settings_grid.addWidget(jitter_movement_label, 2, 2)
        settings_grid.addWidget(self.jitter_movement_spin, 2, 3)

        main_layout.addLayout(settings_grid)

        # Save button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.save_button = self.create_styled_button("Save Parameters", 140)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def _configure_multiplier_spinner(self):
        """Configure multiplier spinner."""
        self.multiple_spin.setRange(1, 20)
        self.multiple_spin.setSuffix("x")
        self.multiple_spin.setMinimumWidth(100)
        self.multiple_spin.setMaximumWidth(120)
        self.multiple_spin.setMaximumHeight(28)
        self.multiple_spin.setFont(QFont("Arial", 10))

    def _configure_sleep_divider_spinner(self):
        """Configure sleep divider spinner."""
        self.sleep_divider_spin.setRange(0.1, 20.0)
        self.sleep_divider_spin.setSingleStep(0.1)
        self.sleep_divider_spin.setSuffix(" div")
        self.sleep_divider_spin.setMinimumWidth(100)
        self.sleep_divider_spin.setMaximumWidth(120)
        self.sleep_divider_spin.setMaximumHeight(28)
        self.sleep_divider_spin.setFont(QFont("Arial", 10))

    def _configure_sleep_suber_spinner(self):
        """Configure sleep suber spinner."""
        self.sleep_suber_spin.setRange(-5.0, 5.0)
        self.sleep_suber_spin.setSingleStep(0.1)
        self.sleep_suber_spin.setSuffix(" ms")
        self.sleep_suber_spin.setMinimumWidth(100)
        self.sleep_suber_spin.setMaximumWidth(120)
        self.sleep_suber_spin.setMaximumHeight(28)
        self.sleep_suber_spin.setFont(QFont("Arial", 10))

    def _configure_sensitivity_spinner(self):
        """Configure sensitivity spinner properties."""
        self.global_sensitivity.setRange(0.1, 10.0)
        self.global_sensitivity.setSingleStep(0.1)
        self.global_sensitivity.setDecimals(2)
        self.global_sensitivity.setSuffix(" sens")
        self.global_sensitivity.setMinimumWidth(100)
        self.global_sensitivity.setMaximumWidth(120)
        self.global_sensitivity.setMaximumHeight(28)
        self.global_sensitivity.setFont(QFont("Arial", 10))

    def _configure_jitter_timing_spinner(self):
        """Configure jitter timing spinner."""
        self.jitter_timing_spin.setRange(0.0, 10.0)
        self.jitter_timing_spin.setSingleStep(0.1)
        self.jitter_timing_spin.setDecimals(1)
        self.jitter_timing_spin.setSuffix(" ms")
        self.jitter_timing_spin.setMinimumWidth(100)
        self.jitter_timing_spin.setMaximumWidth(120)
        self.jitter_timing_spin.setMaximumHeight(28)
        self.jitter_timing_spin.setFont(QFont("Arial", 10))

    def _configure_jitter_movement_spinner(self):
        """Configure jitter movement spinner."""
        self.jitter_movement_spin.setRange(0.0, 100.0)
        self.jitter_movement_spin.setSingleStep(1.0)
        self.jitter_movement_spin.setDecimals(1)
        self.jitter_movement_spin.setSuffix(" %")
        self.jitter_movement_spin.setMinimumWidth(100)
        self.jitter_movement_spin.setMaximumWidth(120)
        self.jitter_movement_spin.setMaximumHeight(28)
        self.jitter_movement_spin.setFont(QFont("Arial", 10))

class FeaturesSection(ConfigSection):
    """Features configuration section."""

    def __init__(self):
        self.section = QGroupBox("Additional Features")
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self.section)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # First row - General features
        first_row = QHBoxLayout()
        first_row.setSpacing(20)

        self.audio_feature = QCheckBox("Audio Notifications")
        self.audio_feature.setChecked(True)
        self.audio_feature.setFont(QFont("Arial", 10))

        self.bomb_timer_feature = QCheckBox("Bomb Timer")
        self.bomb_timer_feature.setChecked(True)
        self.bomb_timer_feature.setFont(QFont("Arial", 10))

        self.auto_accept_feature = QCheckBox("Auto Accept Matches")
        self.auto_accept_feature.setChecked(False)
        self.auto_accept_feature.setFont(QFont("Arial", 10))

        first_row.addWidget(self.audio_feature)
        first_row.addWidget(self.bomb_timer_feature)
        first_row.addWidget(self.auto_accept_feature)
        first_row.addStretch()

        # Second row - Follow RCS configuration
        second_row = QHBoxLayout()
        second_row.setSpacing(15)

        self.follow_rcs_feature = QCheckBox("Follow RCS")
        self.follow_rcs_feature.setChecked(False)
        self.follow_rcs_feature.setFont(QFont("Arial", 10))

        # Color picker button
        color_label = QLabel("Color:")
        color_label.setFont(QFont("Arial", 10))

        self.color_button = QPushButton()
        self.color_button.setMaximumWidth(60)
        self.color_button.setMaximumHeight(28)
        self.color_button.setStyleSheet("background-color: rgb(0, 0, 255);")
        self.current_color = QColor(0, 0, 255, 255)

        # Size slider
        size_label = QLabel("Dot Size:")
        size_label.setFont(QFont("Arial", 10))

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(10)
        self.size_slider.setValue(3)
        self.size_slider.setMaximumWidth(120)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setTickInterval(1)

        self.size_value_label = QLabel("3")
        self.size_value_label.setFont(QFont("Arial", 10))
        self.size_value_label.setMinimumWidth(20)

        second_row.addWidget(self.follow_rcs_feature)
        second_row.addSpacing(10)
        second_row.addWidget(color_label)
        second_row.addWidget(self.color_button)
        second_row.addSpacing(10)
        second_row.addWidget(size_label)
        second_row.addWidget(self.size_slider)
        second_row.addWidget(self.size_value_label)
        second_row.addStretch()

        main_layout.addLayout(first_row)
        main_layout.addLayout(second_row)



class HotkeysSection(ConfigSection):
    """Simplified hotkeys configuration section."""

    def __init__(self):
        self.section = QGroupBox("Keyboard Shortcuts")
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
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(16)

        # System shortcuts section
        self._create_system_hotkeys(main_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)

        # Weapon shortcuts section
        self._create_weapon_hotkeys(main_layout)

        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.save_hotkeys_button = self.create_styled_button("Save Hotkeys", 130)
        save_layout.addWidget(self.save_hotkeys_button)
        save_layout.addStretch()
        main_layout.addLayout(save_layout)

    def _create_system_hotkeys(self, main_layout):
        """Create system hotkey controls."""
        # Title
        title_label = self.create_styled_label("System Shortcuts:", bold=True)
        main_layout.addWidget(title_label)

        # System hotkeys grid
        system_grid = QGridLayout()
        system_grid.setSpacing(8)

        system_hotkeys = [
            ("Toggle Manual RCS:", 'toggle_recoil'),
            ("Toggle Auto Detection:", 'toggle_weapon_detection'),
            ("Exit Application:", 'exit')
        ]

        for i, (label_text, key) in enumerate(system_hotkeys):
            row = i // 2
            col = (i % 2) * 2

            label = QLabel(label_text)
            label.setFont(QFont("Arial", 10))
            label.setMinimumWidth(140)

            combo = QComboBox()
            combo.setMaximumHeight(28)
            combo.setMaximumWidth(100)
            combo.setFont(QFont("Arial", 10))
            for option in self.key_options:
                combo.addItem(option)
            self.hotkey_controls[key] = combo

            system_grid.addWidget(label, row, col)
            system_grid.addWidget(combo, row, col + 1)

        main_layout.addLayout(system_grid)

    def _create_weapon_hotkeys(self, main_layout):
        """Create weapon hotkey controls."""
        # Title
        title_label = self.create_styled_label("Weapon Shortcuts:", bold=True)
        main_layout.addWidget(title_label)

        # Weapon selection row
        weapon_layout = QHBoxLayout()
        weapon_label = QLabel("Weapon:")
        weapon_label.setFont(QFont("Arial", 10))
        weapon_label.setMinimumWidth(80)

        self.weapon_hotkey_combo = QComboBox()
        self.weapon_hotkey_combo.setMaximumHeight(28)
        self.weapon_hotkey_combo.setFont(QFont("Arial", 10))

        key_label = QLabel("Key:")
        key_label.setFont(QFont("Arial", 10))
        key_label.setMinimumWidth(40)

        self.key_hotkey_combo = QComboBox()
        self.key_hotkey_combo.setMaximumHeight(28)
        self.key_hotkey_combo.setMaximumWidth(100)
        self.key_hotkey_combo.setFont(QFont("Arial", 10))

        self.key_hotkey_combo.addItem("None", "")
        for option in self.key_options:
            self.key_hotkey_combo.addItem(option)

        weapon_layout.addWidget(weapon_label)
        weapon_layout.addWidget(self.weapon_hotkey_combo)
        weapon_layout.addSpacing(20)
        weapon_layout.addWidget(key_label)
        weapon_layout.addWidget(self.key_hotkey_combo)
        weapon_layout.addStretch()
        main_layout.addLayout(weapon_layout)

        # Action buttons row
        buttons_layout = QHBoxLayout()
        self.assign_weapon_key_button = self._create_weapon_button("Assign")
        self.remove_weapon_key_button = self._create_weapon_button("Remove")

        buttons_layout.addWidget(self.assign_weapon_key_button)
        buttons_layout.addWidget(self.remove_weapon_key_button)
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

    def _create_weapon_button(self, text: str) -> QPushButton:
        """Create weapon action button."""
        button = QPushButton(text)
        button.setMaximumHeight(28)
        button.setMaximumWidth(80)
        button.setFont(QFont("Arial", 9))
        return button


class ConfigTab(QWidget):
    """Configuration tab with modular architecture."""

    weapon_changed = Signal(str)
    settings_saved = Signal()
    hotkeys_updated = Signal()

    def __init__(self, config_service: ConfigService):
        super().__init__()
        self.logger = logging.getLogger("ConfigTab")
        self.config_service = config_service
        self.follow_rcs_overlay = None

        self.active_weapon_section = ActiveWeaponSection()
        self.weapon_parameters_section = WeaponParametersSection()
        self.features_section = FeaturesSection()
        self.hotkeys_section = HotkeysSection()

        self._setup_ui()
        self._setup_connections()
        self._load_data()
        self.logger.debug("Configuration tab initialized")

    def set_follow_rcs_overlay(self, overlay):
        """Set follow RCS overlay reference for sensitivity updates."""
        self.follow_rcs_overlay = overlay

    def _setup_ui(self):
        """Setup main UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Add sections with consistent spacing
        main_layout.addWidget(self.active_weapon_section.section)
        main_layout.addWidget(self.weapon_parameters_section.section)
        main_layout.addWidget(self.features_section.section)
        main_layout.addWidget(self.hotkeys_section.section)

        # Add stretch to push everything to the top
        main_layout.addStretch()

    def _setup_connections(self):
        """Setup signal connections."""
        # Active weapon selection
        self.active_weapon_section.weapon_combo.currentIndexChanged.connect(
            self._on_weapon_changed)

        # Weapon parameters configuration
        self.weapon_parameters_section.save_button.clicked.connect(
            self._save_weapon_config)

        # Features auto-save
        self.features_section.audio_feature.toggled.connect(
            self._save_features_config)
        self.features_section.bomb_timer_feature.toggled.connect(
            self._save_features_config)
        self.features_section.auto_accept_feature.toggled.connect(
            self._save_features_config)
        self.features_section.follow_rcs_feature.toggled.connect(
            self._save_features_config)

        # Follow RCS configuration
        self.features_section.color_button.clicked.connect(
            self._on_color_button_clicked)
        self.features_section.size_slider.valueChanged.connect(
            self._on_size_slider_changed)

        # Hotkeys
        self.hotkeys_section.save_hotkeys_button.clicked.connect(
            self._save_hotkeys_config)
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
            self.logger.error(f"Data loading failed: {e}")
            QMessageBox.warning(self, "Warning", f"Data loading error: {e}")

    def _populate_weapon_combos(self, combos: List[QComboBox]):
        """Populate a list of combo boxes with weapons from the config service."""
        # Get weapon data, sorted for consistent ordering
        weapon_items = []
        for name in sorted(self.config_service.weapon_profiles.keys()):
            display_name = self.config_service.get_weapon_display_name(name)
            display_name_str = str(display_name) if display_name else name
            weapon_items.append((display_name_str, str(name)))

        # Populate combos
        for combo in combos:
            current_data = combo.currentData()
            combo.clear()
            combo.addItem("Select a weapon...", userData="")
            for display, data in weapon_items:
                combo.addItem(display, userData=data)

            # Restore selection if possible
            if current_data:
                index = combo.findData(current_data)
                if index >= 0:
                    combo.setCurrentIndex(index)

    def _load_global_settings(self):
        """Load global settings."""
        sensitivity = self.config_service.config.get("game_sensitivity", 1.0)
        self.weapon_parameters_section.global_sensitivity.setValue(sensitivity)

    def _load_weapons(self):
        """Load weapons into combo boxes."""
        self._populate_weapon_combos([
            self.active_weapon_section.weapon_combo,
            self.hotkeys_section.weapon_hotkey_combo
        ])

        # Load weapon parameters if a weapon is selected
        current_index = self.active_weapon_section.weapon_combo.currentIndex()
        if current_index > 0:
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

        self.features_section.follow_rcs_feature.setChecked(
            features.get("follow_rcs_enabled", False))

        # Load Follow RCS configuration
        follow_rcs_config = self.config_service.config.get("follow_rcs", {})

        # Load color
        color = follow_rcs_config.get("color", [0, 0, 255, 255])
        self.features_section.current_color = QColor(color[0], color[1], color[2], color[3])
        self.features_section.color_button.setStyleSheet(
            f"background-color: rgb({color[0]}, {color[1]}, {color[2]});")

        # Load dot size
        dot_size = follow_rcs_config.get("dot_size", 3)
        self.features_section.size_slider.setValue(dot_size)
        self.features_section.size_value_label.setText(str(dot_size))

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

        weapon_name = self.active_weapon_section.weapon_combo.currentData()

        if not weapon_name:
            self.weapon_parameters_section.multiple_spin.setValue(0)
            self.weapon_parameters_section.sleep_divider_spin.setValue(1.0)
            self.weapon_parameters_section.sleep_suber_spin.setValue(0.0)
            self.weapon_parameters_section.jitter_timing_spin.setValue(0.0)
            self.weapon_parameters_section.jitter_movement_spin.setValue(0.0)
            self.weapon_changed.emit("")
            return

        weapon = self.config_service.get_weapon_profile(weapon_name)
        if not weapon:
            self.logger.warning(f"Weapon profile not found: {weapon_name}")
            return

        self.weapon_parameters_section.multiple_spin.setValue(weapon.multiple)
        self.weapon_parameters_section.sleep_divider_spin.setValue(weapon.sleep_divider)
        self.weapon_parameters_section.sleep_suber_spin.setValue(weapon.sleep_suber)
        self.weapon_parameters_section.jitter_timing_spin.setValue(weapon.jitter_timing)
        self.weapon_parameters_section.jitter_movement_spin.setValue(weapon.jitter_movement)

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
            self.logger.error(f"Key assignment failed: {e}")
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
            self.logger.error(f"Key removal failed: {e}")
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
            self.logger.error(f"Hotkey validation failed: {e}")
            return False, [f"Validation error: {e}"]

    def _save_weapon_config(self):
        """Save weapon and global configuration."""
        try:
            # Save global sensitivity first
            new_sensitivity = self.weapon_parameters_section.global_sensitivity.value()
            current_sensitivity = self.config_service.config.get("game_sensitivity", 1.0)

            if abs(new_sensitivity - current_sensitivity) > 0.001:
                success = self.config_service.update_global_sensitivity(new_sensitivity)
                if not success:
                    QMessageBox.warning(self, "Warning", "Sensitivity update failed")
                    return
            else:
                self.config_service.config["game_sensitivity"] = new_sensitivity

            # Save weapon-specific configuration if a weapon is selected
            weapon_name = self.active_weapon_section.weapon_combo.currentData()
            if weapon_name:
                weapon = self.config_service.get_weapon_profile(weapon_name)
                if weapon:
                    sensitivity_changed = abs(weapon.game_sensitivity - new_sensitivity) > 0.001

                    # Update weapon parameters
                    weapon.multiple = self.weapon_parameters_section.multiple_spin.value()
                    weapon.sleep_divider = self.weapon_parameters_section.sleep_divider_spin.value()
                    weapon.sleep_suber = self.weapon_parameters_section.sleep_suber_spin.value()
                    weapon.jitter_timing = self.weapon_parameters_section.jitter_timing_spin.value()
                    weapon.jitter_movement = self.weapon_parameters_section.jitter_movement_spin.value()

                    if sensitivity_changed:
                        success = self.config_service.update_weapon_sensitivity(weapon_name, new_sensitivity)
                        if not success:
                            QMessageBox.warning(self, "Warning", "Weapon sensitivity update failed")
                            return
                    else:
                        weapon.recalculate_pattern()

                    # Save weapon profile
                    success = self.config_service.save_weapon_profile(weapon)
                    if not success:
                        QMessageBox.warning(self, "Warning", "Weapon profile save failed")
                        return

            # Update follow RCS overlay sensitivity if changed
            if self.follow_rcs_overlay and abs(new_sensitivity - current_sensitivity) > 0.001:
                self.follow_rcs_overlay.set_sensitivity(new_sensitivity)

            # Save global config
            success = self.config_service.save_config()
            if success:
                QMessageBox.information(self, "Success", "Configuration saved successfully")
                self.settings_saved.emit()
            else:
                QMessageBox.warning(self, "Warning", "Configuration save failed")

        except Exception as e:
            self.logger.error(f"Configuration save failed: {e}")
            QMessageBox.critical(self, "Error", f"Save error: {e}")

    def _on_color_button_clicked(self):
        """Handle color button click to open color picker."""
        color = QColorDialog.getColor(
            self.features_section.current_color,
            self,
            "Select Follow RCS Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )

        if color.isValid():
            self.features_section.current_color = color
            self.features_section.color_button.setStyleSheet(
                f"background-color: rgb({color.red()}, {color.green()}, {color.blue()});")
            self._save_follow_rcs_config()

    def _on_size_slider_changed(self, value):
        """Handle size slider value change."""
        self.features_section.size_value_label.setText(str(value))
        self._save_follow_rcs_config()

    def _save_follow_rcs_config(self):
        """Save Follow RCS configuration."""
        try:
            color = self.features_section.current_color
            follow_rcs_config = {
                "dot_size": self.features_section.size_slider.value(),
                "color": [color.red(), color.green(), color.blue(), color.alpha()]
            }
            self.config_service.config["follow_rcs"] = follow_rcs_config

            success = self.config_service.save_config()

            if success:
                # Update overlay if it exists
                if self.follow_rcs_overlay:
                    self.follow_rcs_overlay.set_dot_size(follow_rcs_config["dot_size"])
                    self.follow_rcs_overlay.set_color(follow_rcs_config["color"])

                self.logger.debug("Follow RCS configuration saved")
            else:
                self.logger.warning("Failed to save Follow RCS configuration")

        except Exception as e:
            self.logger.error(f"Follow RCS config save failed: {e}")

    def _save_features_config(self):
        """Save features configuration."""
        try:
            features_settings = {
                "tts_enabled": self.features_section.audio_feature.isChecked(),
                "bomb_timer_enabled": self.features_section.bomb_timer_feature.isChecked(),
                "auto_accept_enabled": self.features_section.auto_accept_feature.isChecked(),
                "follow_rcs_enabled": self.features_section.follow_rcs_feature.isChecked()
            }
            self.config_service.config["features"] = features_settings

            success = self.config_service.save_config()

            if success:
                # Emit signal to notify about the change
                self.settings_saved.emit()
                self.logger.debug("Features configuration saved")
            else:
                self.logger.warning("Failed to save features configuration")

        except Exception as e:
            self.logger.error(f"Features config save failed: {e}")

    def _save_hotkeys_config(self):
        """Save hotkeys configuration with conflict validation."""
        try:
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
            self.logger.error(f"Hotkeys save failed: {e}")
            QMessageBox.critical(self, "Error", f"Save error: {e}")

    def get_selected_weapon(self) -> str:
        """Get currently selected weapon name."""
        index = self.active_weapon_section.weapon_combo.currentIndex()
        if index < 0:
            return ""
        return self.active_weapon_section.weapon_combo.currentData() or ""

    def set_weapon_controls_enabled(self, enabled: bool):
        """Enable/disable weapon selection controls based on automatic detection status."""
        try:
            self.active_weapon_section.weapon_combo.setEnabled(enabled)

            if not enabled:
                self.active_weapon_section.weapon_combo.setToolTip(
                    "Weapon selection disabled - Automatic weapon detection is active")
            else:
                self.active_weapon_section.weapon_combo.setToolTip(
                    "Select the active weapon for recoil compensation")

        except Exception as e:
            self.logger.error(f"Weapon controls state update error: {e}")
