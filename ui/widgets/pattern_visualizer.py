"""
Matplotlib-based widget for recoil pattern visualization.
"""
import logging
from typing import List, Tuple, Optional

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QSizePolicy

from core.models.recoil_data import RecoilData


class PlotConfiguration:
    """Configuration constants for plot appearance."""

    DEFAULT_WIDTH = 6
    DEFAULT_HEIGHT = 5
    DEFAULT_DPI = 100

    # Colors
    DEFAULT_LINE_COLOR = 'b'
    DEFAULT_POINT_COLOR = 'r'
    DEFAULT_LINE_WIDTH = 2
    DEFAULT_POINT_SIZE = 5

    # Grid
    GRID_ALPHA = 0.6
    GRID_LINESTYLE = '--'

    # Margins
    VIEW_PADDING = 0.2  # 20% padding around pattern
    MIN_RANGE = 1  # Minimum axis range

    # Text
    FONT_SIZE_NUMBERS = 8
    TEXT_OFFSET_H = 'right'
    TEXT_OFFSET_V = 'bottom'


class PatternCalculator:
    """Handles pattern position calculations."""

    @staticmethod
    def calculate_cumulative_positions(pattern_data: List[RecoilData],
                                       invert_y: bool = False) -> np.ndarray:
        """
        Calculate cumulative positions from recoil data.

        Args:
            pattern_data: List of recoil data points
            invert_y: Whether to invert Y axis

        Returns:
            Array of cumulative positions [(x, y), ...]
        """
        if not pattern_data:
            return np.array([[0.0, 0.0]])

        positions = [(0.0, 0.0)]

        for point in pattern_data:
            last_x, last_y = positions[-1]
            if invert_y:
                new_position = (last_x + point.dx, last_y - point.dy)
            else:
                new_position = (last_x + point.dx, last_y + point.dy)
            positions.append(new_position)

        return np.array(positions)

    @staticmethod
    def calculate_view_bounds(positions: np.ndarray,
                              padding: float = PlotConfiguration.VIEW_PADDING) -> Tuple[float,
                                                                                        float,
                                                                                        float,
                                                                                        float]:
        """
        Calculate optimal view bounds for positions.

        Args:
            positions: Array of positions
            padding: Padding percentage around bounds

        Returns:
            Tuple of (x_min, x_max, y_min, y_max)
        """
        if len(positions) <= 1:
            return (-1, 1, -1, 1)

        x_min, x_max = positions[:, 0].min(), positions[:, 0].max()
        y_min, y_max = positions[:, 1].min(), positions[:, 1].max()

        x_range = max(abs(x_max - x_min), PlotConfiguration.MIN_RANGE)
        y_range = max(abs(y_max - y_min), PlotConfiguration.MIN_RANGE)

        max_range = max(x_range, y_range)
        if x_range < max_range * 0.2:
            x_range = max_range * 0.3
        if y_range < max_range * 0.2:
            y_range = max_range * 0.3

        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2

        x_min_padded = x_center - x_range * (0.5 + padding)
        x_max_padded = x_center + x_range * (0.5 + padding)
        y_min_padded = y_center - y_range * (0.5 + padding)
        y_max_padded = y_center + y_range * (0.5 + padding)

        return (x_min_padded, x_max_padded, y_min_padded, y_max_padded)


class PlotRenderer:
    """Handles matplotlib plot rendering."""

    def __init__(self, axes):
        self.axes = axes
        self.logger = logging.getLogger("PlotRenderer")

    def clear_plot(self):
        """Clear the plot completely."""
        self.axes.clear()
        self._setup_axes()

    def _setup_axes(self):
        """Setup axes with default configuration."""
        self.axes.set_aspect('equal')
        self.axes.grid(True, linestyle=PlotConfiguration.GRID_LINESTYLE,
                       alpha=PlotConfiguration.GRID_ALPHA)
        self.axes.set_title("Recoil Pattern")
        self.axes.set_xlabel("X Displacement")
        self.axes.set_ylabel("Y Displacement")

    def render_pattern(self, positions: np.ndarray, show_points: bool,
                       show_numbers: bool, line_color: str, point_color: str,
                       line_width: int, point_size: int):
        """
        Render pattern on the plot.

        Args:
            positions: Cumulative positions array
            show_points: Whether to show individual points
            show_numbers: Whether to show point numbers
            line_color: Color for lines
            point_color: Color for points
            line_width: Width of lines
            point_size: Size of points
        """
        # Draw connecting lines
        self.axes.plot(positions[:, 0], positions[:, 1],
                       linestyle='-', color=line_color, linewidth=line_width)

        # Draw points if enabled
        if show_points:
            self.axes.plot(positions[:, 0], positions[:, 1],
                           linestyle='None', marker='o', color=point_color,
                           markersize=point_size)

            # Add point numbers if enabled
            if show_numbers:
                self._add_point_numbers(positions)

    def _add_point_numbers(self, positions: np.ndarray):
        """Add numbers to each point."""
        for i, (x, y) in enumerate(positions):
            self.axes.text(x, y, str(i),
                           fontsize=PlotConfiguration.FONT_SIZE_NUMBERS,
                           ha=PlotConfiguration.TEXT_OFFSET_H,
                           va=PlotConfiguration.TEXT_OFFSET_V)

    def set_view_bounds(self, bounds: Tuple[float, float, float, float]):
        """Set plot view bounds."""
        x_min, x_max, y_min, y_max = bounds
        self.axes.set_xlim(x_min, x_max)
        self.axes.set_ylim(y_min, y_max)

    def toggle_grid(self, show: bool):
        """Toggle grid display."""
        if show:
            self.axes.grid(True, linestyle=PlotConfiguration.GRID_LINESTYLE,
                           alpha=PlotConfiguration.GRID_ALPHA)
        else:
            self.axes.grid(False)


class PatternVisualizer(FigureCanvasQTAgg):
    """Matplotlib-based recoil pattern visualization widget."""

    def __init__(
            self,
            parent=None,
            width=PlotConfiguration.DEFAULT_WIDTH,
            height=PlotConfiguration.DEFAULT_HEIGHT,
            dpi=PlotConfiguration.DEFAULT_DPI):
        """
        Initialize the pattern visualizer.

        Args:
            parent: Parent widget
            width: Figure width in inches
            height: Figure height in inches
            dpi: Dots per inch resolution
        """
        self.logger = logging.getLogger("PatternVisualizer")

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)

        super().__init__(self.fig)
        self.setParent(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.updateGeometry()

        self.pattern_data: List[RecoilData] = []
        self.show_points = True
        self.show_numbers = False
        self.invert_y = False
        self.line_color = PlotConfiguration.DEFAULT_LINE_COLOR
        self.point_color = PlotConfiguration.DEFAULT_POINT_COLOR
        self.line_width = PlotConfiguration.DEFAULT_LINE_WIDTH
        self.point_size = PlotConfiguration.DEFAULT_POINT_SIZE

        self.calculator = PatternCalculator()
        self.plot_renderer = PlotRenderer(
            self.axes)  # RENAMED from self.renderer

        self.plot_renderer._setup_axes()
        self.fig.tight_layout()

        self.logger.debug("Pattern visualizer initialized")

    def set_pattern(self, pattern_data: List[RecoilData]) -> None:
        """
        Set pattern data and refresh visualization.

        Args:
            pattern_data: List of recoil data points
        """
        self.pattern_data = pattern_data.copy() if pattern_data else []
        self.redraw()

    def clear_pattern(self) -> None:
        """Clear pattern data and visualization."""
        try:
            self.pattern_data = []
            self.plot_renderer.clear_plot()
            self.fig.tight_layout()
            self.draw()
        except Exception as e:
            self.logger.error(f"Failed to clear pattern: {e}")
            # Last resort - just clear data
            self.pattern_data = []

    def has_pattern(self) -> bool:
        """Check if pattern data is available."""
        return bool(self.pattern_data)

    def toggle_points(self, show: bool) -> None:
        """Toggle point display."""
        self.show_points = show
        self.redraw()

    def toggle_numbers(self, show: bool) -> None:
        """Toggle point number display."""
        self.show_numbers = show
        self.redraw()

    def toggle_grid(self, show: bool) -> None:
        """Toggle grid display."""
        self.plot_renderer.toggle_grid(show)
        self.draw()

    def set_invert_y(self, invert: bool) -> None:
        """Set Y-axis inversion."""
        self.invert_y = invert
        self.redraw()

    def set_colors(self, point_color: Optional[str] = None,
                   line_color: Optional[str] = None) -> None:
        """
        Set visualization colors.

        Args:
            point_color: Color for points (matplotlib format)
            line_color: Color for lines (matplotlib format)
        """
        if point_color is not None:
            self.point_color = point_color
        if line_color is not None:
            self.line_color = line_color
        self.redraw()

    def redraw(self) -> None:
        """Redraw the complete visualization."""
        try:
            if not self.pattern_data:
                self.clear_pattern()
                return

            # Clear and setup
            self.plot_renderer.clear_plot()

            # Calculate positions
            positions = self.calculator.calculate_cumulative_positions(
                self.pattern_data, self.invert_y
            )

            # Render pattern
            self.plot_renderer.render_pattern(
                positions, self.show_points, self.show_numbers,
                self.line_color, self.point_color,
                self.line_width, self.point_size
            )

            # Set optimal view
            bounds = self.calculator.calculate_view_bounds(positions)
            self.plot_renderer.set_view_bounds(bounds)

            # Finalize
            self.fig.tight_layout()
            self.draw()

            self.logger.debug(f"Pattern redrawn ({len(self.pattern_data)} points)")

        except Exception as e:
            self.logger.error(f"Pattern redraw failed: {e}")
            # Try to recover by clearing and redrawing empty
            try:
                self.clear_pattern()
            except Exception:
                pass  # If clear fails too, just give up silently

    def reset_view(self) -> None:
        """Reset view to show entire pattern optimally."""
        if not self.pattern_data:
            return

        positions = self.calculator.calculate_cumulative_positions(
            self.pattern_data, self.invert_y
        )
        bounds = self.calculator.calculate_view_bounds(positions)
        self.plot_renderer.set_view_bounds(bounds)
        self.draw()

    def export_figure(self, filename: str, format: str = 'png', dpi: int = 300,
                      **kwargs) -> bool:
        """
        Export figure to file.

        Args:
            filename: Output filename
            format: Export format (png, pdf, svg, etc.)
            dpi: Resolution in dots per inch
            kwargs: Additional matplotlib savefig parameters

        Returns:
            True if export successful
        """
        try:
            # Default export parameters
            export_params = {
                'dpi': dpi,
                'bbox_inches': 'tight',
                'facecolor': 'white',
                'edgecolor': 'none'
            }
            export_params.update(kwargs)

            self.fig.savefig(filename, format=format, **export_params)
            self.logger.info(f"Figure exported: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Figure export failed: {e}")
            return False
