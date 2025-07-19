"""
Visualization tab for recoil pattern display with optimized external styles.
"""
import logging
import time
from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QComboBox,
    QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import QTimer, pyqtSignal
from matplotlib.backends.backend_qt import NavigationToolbar2QT

from core.services.config_service import ConfigService
from ui.widgets.pattern_visualizer import PatternVisualizer


class VisualizationControls:
    """Encapsulates visualization control widgets."""

    def __init__(self):
        self.widget = QWidget()
        self._setup_controls()

    def _setup_controls(self):
        """Setup visualization control widgets."""
        layout = QVBoxLayout(self.widget)

        # Display options
        options_layout = QHBoxLayout()

        self.show_grid = QCheckBox("Show Grid")
        self.show_grid.setChecked(True)

        self.show_points = QCheckBox("Show Points")
        self.show_points.setChecked(True)

        self.show_numbers = QCheckBox("Show Numbers")
        self.show_numbers.setChecked(False)

        self.invert_y = QCheckBox("Invert Y Axis")
        self.invert_y.setChecked(False)

        options_layout.addWidget(self.show_grid)
        options_layout.addWidget(self.show_points)
        options_layout.addWidget(self.show_numbers)
        options_layout.addWidget(self.invert_y)
        options_layout.addStretch()

        layout.addLayout(options_layout)

        # Style and export controls
        controls_layout = QHBoxLayout()

        # Color style selection
        style_layout = QHBoxLayout()
        style_layout.addWidget(QLabel("Style:"))

        self.style_combo = QComboBox()
        self._populate_style_combo()
        style_layout.addWidget(self.style_combo)

        controls_layout.addLayout(style_layout)
        controls_layout.addStretch()

        # Export button
        self.export_button = QPushButton("Export...")
        controls_layout.addWidget(self.export_button)

        layout.addLayout(controls_layout)

        # Info label
        info_label = QLabel(
            "Use the toolbar above to zoom, pan, and export the chart"
        )
        info_label.setStyleSheet("font-style: italic; color: gray;")
        layout.addWidget(info_label)

    def _populate_style_combo(self):
        """Populate style combo with color options."""
        styles = [
            ("Standard (Blue/Red)", ["b", "r"]),
            ("Green/Orange", ["g", "orange"]),
            ("Black/Gray", ["k", "gray"]),
            ("Purple/Cyan", ["purple", "cyan"])
        ]

        for display_name, colors in styles:
            self.style_combo.addItem(display_name, colors)


class VisualizationTab(QWidget):
    """Visualization tab with externalized styles and modular controls."""

    # Signal for thread-safe weapon updates
    _weapon_update_requested = pyqtSignal(str)

    def __init__(self, config_service: ConfigService):
        super().__init__()

        self.logger = logging.getLogger("VisualizationTab")
        self.config_service = config_service
        self.current_weapon = None

        # Protection contre les mises à jour rapides
        self._update_in_progress = False
        self._pending_weapon = None
        self._last_update_time = 0
        self._debounce_delay = 0.1  # 100ms

        # Timer pour les mises à jour différées (must be created in main thread)
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._process_pending_update)

        # Connect signal to slot for thread-safe updates
        self._weapon_update_requested.connect(self._handle_weapon_update_signal)

        # Initialize components
        self.pattern_visualizer = PatternVisualizer(width=6, height=5, dpi=100)
        self.controls = VisualizationControls()

        self._setup_ui()
        self._setup_connections()

        self.logger.debug("Visualization tab initialized")

    def _setup_ui(self):
        """Configure the user interface."""
        main_layout = QVBoxLayout(self)

        # Matplotlib visualizer
        main_layout.addWidget(self.pattern_visualizer)

        # Matplotlib toolbar
        self.matplotlib_toolbar = NavigationToolbar2QT(
            self.pattern_visualizer, self)
        main_layout.addWidget(self.matplotlib_toolbar)

        # Controls widget
        main_layout.addWidget(self.controls.widget)

        # Flexible space at bottom
        main_layout.addStretch()

    def _setup_connections(self):
        """Configure signal connections."""
        # Visualization options
        self.controls.show_grid.toggled.connect(
            self.pattern_visualizer.toggle_grid)
        self.controls.show_points.toggled.connect(
            self.pattern_visualizer.toggle_points)
        self.controls.show_numbers.toggled.connect(
            self.pattern_visualizer.toggle_numbers)
        self.controls.invert_y.toggled.connect(
            self.pattern_visualizer.set_invert_y)

        # Style control
        self.controls.style_combo.currentIndexChanged.connect(
            self._on_style_changed)

        # Export functionality
        self.controls.export_button.clicked.connect(self._export_figure)

    def _process_pending_update(self):
        """Traite les mises à jour en attente."""
        if self._pending_weapon and not self._update_in_progress:
            weapon_name = self._pending_weapon
            self._pending_weapon = None
            self._do_update_weapon_visualization(weapon_name)

    def update_weapon_visualization(self, weapon_name: Optional[str]):
        """
        Update visualization with specified weapon pattern with debouncing.
        Thread-safe: can be called from any thread.

        Args:
            weapon_name: Name of weapon to visualize, or None to clear
        """
        # Handle weapon clearing (None or empty string)
        if not weapon_name:
            # Use signal for thread-safe clearing
            self._weapon_update_requested.emit("")
            return

        # Skip if same weapon to avoid unnecessary updates
        if self.current_weapon == weapon_name:
            return

        # Use signal for thread-safe update
        self._weapon_update_requested.emit(weapon_name)

    def _handle_weapon_update_signal(self, weapon_name: str):
        """
        Handle weapon update signal in main thread.
        This method is guaranteed to run in the main GUI thread.
        """
        # Handle weapon clearing
        if not weapon_name:
            self._clear_visualization()
            self.current_weapon = None
            return

        current_time = time.time()

        # Si une mise à jour est en cours, stocker la demande pour plus tard
        if self._update_in_progress:
            self._pending_weapon = weapon_name
            return

        # Debouncing : si c'est trop rapide, différer la mise à jour
        time_since_last = current_time - self._last_update_time
        if time_since_last < self._debounce_delay:
            self._pending_weapon = weapon_name
            remaining_time = int((self._debounce_delay - time_since_last) * 1000)
            # Now safe to start timer since we're in main thread
            self._update_timer.start(remaining_time)
            return

        # Effectuer la mise à jour immédiatement
        self._do_update_weapon_visualization(weapon_name)

    def _do_update_weapon_visualization(self, weapon_name: str):
        """Effectue réellement la mise à jour de la visualisation."""
        if self._update_in_progress:
            return

        self._update_in_progress = True
        self._last_update_time = time.time()

        try:
            # Get weapon profile
            weapon = self.config_service.get_weapon_profile(weapon_name)
            if not weapon:
                self.logger.warning("Weapon profile not found: %s", weapon_name)
                self._clear_visualization()
                return

            # Update visualizer with safety check
            if hasattr(weapon, 'recoil_pattern') and weapon.recoil_pattern:
                self.pattern_visualizer.set_pattern(weapon.recoil_pattern)
            else:
                self.logger.warning("No recoil pattern for weapon: %s", weapon_name)
                self._clear_visualization()
                return

            # Store current weapon
            self.current_weapon = weapon_name

            self.logger.debug("Visualization updated: %s", weapon_name)

        except Exception as e:
            self.logger.error("Visualization update failed: %s", e)
            # Don't show popup for rapid switching errors - just log them
            if "bbox" not in str(e):
                QMessageBox.warning(self, "Warning", f"Visualization error: {e}")
        finally:
            self._update_in_progress = False

            # Traiter les mises à jour en attente s'il y en a
            if self._pending_weapon:
                self._pending_weapon = None
                # Programmer la prochaine mise à jour avec un petit délai
                self._update_timer.start(50)  # 50ms de délai

    def _clear_visualization(self):
        """Clear the visualization display."""
        try:
            self.pattern_visualizer.clear_pattern()
            self.current_weapon = None
        except Exception as e:
            self.logger.error("Failed to clear visualization: %s", e)

    def _on_style_changed(self, index):
        """
        Handle visualization style change.

        Args:
            index: Index of selected style
        """
        if index < 0:
            return

        try:
            # Get selected colors
            colors = self.controls.style_combo.currentData()
            if not colors or len(colors) < 2:
                return

            # Update visualizer colors
            self.pattern_visualizer.set_colors(
                point_color=colors[1],
                line_color=colors[0]
            )
        except Exception as e:
            self.logger.error("Failed to change style: %s", e)

    def _export_figure(self):
        """Export the visualization figure to file."""
        try:
            # Generate default filename
            if self.current_weapon:
                default_filename = f"pattern_{self.current_weapon}.png"
            else:
                default_filename = "pattern.png"

            # File dialog
            options = QFileDialog.Options()
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Figure",
                default_filename,
                "PNG Images (*.png);;JPEG Images (*.jpg);;PDF Documents (*.pdf);;SVG Images (*.svg)",
                options=options
            )

            if not filename:
                return

            # Determine format from extension
            format_map = {
                '.png': 'png',
                '.jpg': 'jpg',
                '.jpeg': 'jpg',
                '.pdf': 'pdf',
                '.svg': 'svg'
            }

            import os
            ext = os.path.splitext(filename)[1].lower()
            export_format = format_map.get(ext, 'png')

            # Export figure
            success = self.pattern_visualizer.export_figure(
                filename, format=export_format)

            if success:
                QMessageBox.information(
                    self, "Success", f"Figure exported: {filename}")
                self.logger.info("Figure exported successfully: %s", filename)
            else:
                QMessageBox.warning(self, "Warning", "Export failed")
                self.logger.warning("Figure export failed: %s", filename)

        except Exception as e:
            self.logger.error("Figure export error: %s", e)
            QMessageBox.critical(self, "Error", f"Export error: {e}")

    def get_visualization_info(self) -> dict:
        """Get current visualization information."""
        return {
            "current_weapon": self.current_weapon,
            "has_pattern": self.pattern_visualizer.has_pattern(),
            "visualization_options": {
                "show_grid": self.controls.show_grid.isChecked(),
                "show_points": self.controls.show_points.isChecked(),
                "show_numbers": self.controls.show_numbers.isChecked(),
                "invert_y": self.controls.invert_y.isChecked()
            },
            "style": {
                "selected_index": self.controls.style_combo.currentIndex(),
                "selected_text": self.controls.style_combo.currentText(),
                "colors": self.controls.style_combo.currentData()
            }
        }

    def apply_visualization_settings(self, settings: dict):
        """Apply visualization settings from configuration."""
        try:
            options = settings.get("visualization_options", {})

            # Apply display options
            self.controls.show_grid.setChecked(options.get("show_grid", True))
            self.controls.show_points.setChecked(
                options.get("show_points", True))
            self.controls.show_numbers.setChecked(
                options.get("show_numbers", False))
            self.controls.invert_y.setChecked(options.get("invert_y", False))

            # Apply style
            style_settings = settings.get("style", {})
            style_index = style_settings.get("selected_index", 0)
            if 0 <= style_index < self.controls.style_combo.count():
                self.controls.style_combo.setCurrentIndex(style_index)

            self.logger.debug("Visualization settings applied")

        except Exception as e:
            self.logger.error("Failed to apply visualization settings: %s", e)

    def reset_view(self):
        """Reset visualization to default view."""
        try:
            # Reset display options to defaults
            self.controls.show_grid.setChecked(True)
            self.controls.show_points.setChecked(True)
            self.controls.show_numbers.setChecked(False)
            self.controls.invert_y.setChecked(False)

            # Reset style to first option
            self.controls.style_combo.setCurrentIndex(0)

            # Reset matplotlib view
            self.pattern_visualizer.reset_view()

            self.logger.debug("Visualization view reset")

        except Exception as e:
            self.logger.error("Failed to reset view: %s", e)

    def get_export_formats(self) -> List[str]:
        """Get list of supported export formats."""
        return ['png', 'jpg', 'pdf', 'svg']

    def export_with_settings(self, filename: str, export_format: str = 'png',
                             dpi: int = 300, **kwargs) -> bool:
        """
        Export figure with specific settings.

        Args:
            filename: Output filename
            export_format: Export format (png, jpg, pdf, svg)
            dpi: Resolution in DPI
            kwargs: Additional export parameters

        Returns:
            True if export successful
        """
        try:
            success = self.pattern_visualizer.export_figure(
                filename, format=export_format, dpi=dpi, **kwargs
            )

            if success:
                self.logger.info("Figure exported with settings: %s", filename)
            else:
                self.logger.warning("Export failed: %s", filename)

            return success

        except Exception as e:
            self.logger.error("Export with settings failed: %s", e)
            return False
