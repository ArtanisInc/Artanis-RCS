"""
Follow RCS Overlay Widget - Shows dot following recoil pattern.
"""
import logging
from typing import Optional
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPaintEvent, QCloseEvent

from data.config_repository import CSVRepository


class FollowRCSOverlay(QWidget):
    """Overlay widget displaying dot that follows recoil pattern."""

    def __init__(self, sensitivity: float, dot_size: int = 3, dot_color: Optional[QColor] = None, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger("FollowRCSOverlay")

        self.offset_x = 0.0
        self.offset_y = 0.0
        self.dot_size = dot_size
        self.dot_color = dot_color if dot_color else QColor(0, 0, 255, 255)
        self.outline_color = QColor(0, 0, 0, 255)

        self.offsetmark = 3.1
        self.sensitivity = sensitivity
        self.modifier = self._calculate_modifier()

        self.is_active = False

        self._setup_ui()
        self._setup_timer()
        self.hide()

        self.logger.debug("Follow RCS overlay initialized")

    def _calculate_modifier(self) -> float:
        """Calculate scale modifier for mouse to screen pixel conversion."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_height = screen.geometry().height()
            return self.offsetmark * CSVRepository.SENSITIVITY_MULTIPLIER / self.sensitivity / screen_height * 1080
        return 6.2

    def _setup_ui(self):
        """Setup the user interface."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            window_size = 400
            self.setFixedSize(window_size, window_size)

            x_pos = (screen_geometry.width() - window_size) // 2
            y_pos = (screen_geometry.height() - window_size) // 2
            self.move(x_pos, y_pos)

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _setup_timer(self):
        """Setup the update timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(16)

    def update_position(self, offset_x: float, offset_y: float):
        """Update dot position based on recoil pattern."""
        if not self.is_active:
            return
        self.offset_x = offset_x / self.modifier
        self.offset_y = offset_y / self.modifier

    def set_active(self, active: bool):
        """Enable or disable the overlay."""
        self.is_active = active
        self.offset_x = 0.0
        self.offset_y = 0.0

        if active:
            self.show()
        else:
            self.hide()

    def paintEvent(self, event: Optional[QPaintEvent]):
        """Paint the dot overlay."""
        if not self.is_active:
            return

        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            center_x = self.width() // 2
            center_y = self.height() // 2
            dot_x = center_x + int(self.offset_x)
            dot_y = center_y + int(self.offset_y)

            is_compensating = abs(self.offset_x) > 0.1 or abs(self.offset_y) > 0.1
            self._draw_dot(painter, dot_x, dot_y, is_compensating)
        except Exception as e:
            self.logger.error(f"Paint event error: {e}")

    def _draw_dot(self, painter: QPainter, x: int, y: int, is_compensating: bool):
        """Draw a simple dot at specified position."""
        if not is_compensating:
            return

        painter.setPen(Qt.PenStyle.NoPen)

        # Outline
        painter.setBrush(self.outline_color)
        painter.drawEllipse(
            x - self.dot_size // 2 - 1,
            y - self.dot_size // 2 - 1,
            self.dot_size + 2,
            self.dot_size + 2
        )

        # Main dot
        painter.setBrush(self.dot_color)
        painter.drawEllipse(
            x - self.dot_size // 2,
            y - self.dot_size // 2,
            self.dot_size,
            self.dot_size
        )

    def set_dot_style(self, size: int = 4, color: Optional[QColor] = None):
        """Configure dot appearance."""
        self.dot_size = size
        if color:
            self.dot_color = color
        self.update()

    def set_dot_size(self, size: int):
        """Set dot size."""
        self.dot_size = size
        self.update()

    def set_color(self, color):
        """Set dot color from RGBA list or QColor."""
        if isinstance(color, list):
            self.dot_color = QColor(color[0], color[1], color[2], color[3])
        else:
            self.dot_color = color
        self.update()

    def set_sensitivity(self, sensitivity: float, offsetmark: float = 3.1):
        """Configure the sensitivity for converting mouse movement to screen pixels."""
        self.sensitivity = sensitivity
        self.offsetmark = offsetmark
        self.modifier = self._calculate_modifier()

    def closeEvent(self, event: Optional[QCloseEvent]):
        """Handle close event."""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        if event:
            event.accept()
