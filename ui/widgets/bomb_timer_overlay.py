"""
Bomb Timer Overlay Widget for CS2 bomb countdown display.
"""
import logging
from typing import Optional
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QColor, QFontMetrics, QPaintEvent, QCloseEvent


class BombTimerOverlay(QWidget):
    """Overlay widget displaying bomb countdown timer with circular progress."""

    # Signals
    timer_expired = pyqtSignal()
    defuse_alert = pyqtSignal(bool)  # can_defuse

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger("BombTimerOverlay")

        # Timer state
        self.remaining_time = 0.0
        self.max_time = 40.0
        self.has_defuse_kit = False
        self.can_defuse = False
        self.is_active = False

        # Visual settings
        self.widget_size = 160
        self.circle_radius = 60
        self.circle_thickness = 8
        self.font_size = 16

        # Colors
        self.safe_color = QColor(46, 204, 113)  # Green
        self.warning_color = QColor(241, 196, 15)  # Yellow
        self.danger_color = QColor(231, 76, 60)  # Red
        self.defuse_color = QColor(52, 152, 219)  # Blue
        self.background_color = QColor(44, 62, 80)  # Dark blue-gray

        # Setup widget
        self._setup_ui()
        self._setup_timer()

        # Initially hidden
        self.hide()

        self.logger.debug("Bomb timer overlay initialized")

    def _setup_ui(self):
        """Setup the user interface."""
        self.setFixedSize(self.widget_size, self.widget_size)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        # Try translucent background again now that threading is fixed
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set transparent background style
        self.setStyleSheet("background-color: transparent;")

        # Set initial position (top-right corner)
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x_pos = screen_geometry.width() - self.widget_size - 50  # 50px from right edge
            y_pos = 50  # 50px from top
            self.move(x_pos, y_pos)

    def _setup_timer(self):
        """Setup the update timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(50)  # Update every 50ms for smooth animation

    def update_bomb_state(self, remaining_time: float, has_defuse_kit: bool, can_defuse: bool):
        """Update bomb timer state."""
        self.logger.debug(f"Overlay update: time={remaining_time:.1f}, kit={has_defuse_kit}, can_defuse={can_defuse}")

        self.remaining_time = remaining_time
        self.has_defuse_kit = has_defuse_kit
        self.can_defuse = can_defuse

        # Show/hide based on remaining time
        if remaining_time > 0:
            if not self.is_active:
                self.is_active = True
                self.show()
                self.logger.debug("Bomb timer overlay shown")
        else:
            if self.is_active:
                self.is_active = False
                self.hide()
                self.logger.debug("Bomb timer overlay hidden")

    def paintEvent(self, a0: Optional[QPaintEvent]):
        """Paint the bomb timer overlay."""
        if not self.is_active or self.remaining_time <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate center and dimensions
        center_x = self.width() // 2
        center_y = self.height() // 2

        # Draw background circle
        self._draw_background_circle(painter, center_x, center_y)

        # Draw progress arc
        self._draw_progress_arc(painter, center_x, center_y)

        # Draw timer text
        self._draw_timer_text(painter, center_x, center_y)

        # Draw defuse kit indicator
        if self.has_defuse_kit:
            self._draw_defuse_kit_indicator(painter, center_x, center_y)

    def _draw_background_circle(self, painter: QPainter, center_x: int, center_y: int):
        """Draw the background circle."""
        # Semi-transparent dark background for better visibility
        painter.setBrush(QBrush(QColor(0, 0, 0, 120)))  # Dark with some transparency
        painter.setPen(QPen(QColor(100, 100, 100, 180), 2))  # Light gray border
        painter.drawEllipse(
            center_x - self.circle_radius - 10,
            center_y - self.circle_radius - 10,
            (self.circle_radius + 10) * 2,
            (self.circle_radius + 10) * 2
        )

    def _draw_progress_arc(self, painter: QPainter, center_x: int, center_y: int):
        """Draw the circular progress arc."""
        # Calculate progress (0.0 to 1.0)
        progress = self.remaining_time / self.max_time

        # Determine color based on time and defuse ability
        if self.can_defuse:
            color = self.safe_color
        elif self.remaining_time <= 10.0:
            color = self.danger_color
        elif self.remaining_time <= 20.0:
            color = self.warning_color
        else:
            color = self.safe_color

        # Draw progress arc
        pen = QPen(color, self.circle_thickness)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Arc parameters (starts at top, goes clockwise)
        start_angle = -90 * 16  # -90 degrees in 16th of degrees
        span_angle = int(-360 * 16 * progress)  # Negative for clockwise

        painter.drawArc(
            center_x - self.circle_radius,
            center_y - self.circle_radius,
            self.circle_radius * 2,
            self.circle_radius * 2,
            start_angle,
            span_angle
        )

        # Draw background arc (remaining time)
        if progress < 1.0:
            pen_bg = QPen(QColor(255, 255, 255, 50), self.circle_thickness)
            pen_bg.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_bg)

            painter.drawArc(
                center_x - self.circle_radius,
                center_y - self.circle_radius,
                self.circle_radius * 2,
                self.circle_radius * 2,
                start_angle + span_angle,
                -360 * 16 - span_angle
            )

    def _draw_timer_text(self, painter: QPainter, center_x: int, center_y: int):
        """Draw the timer text in the center."""
        # Format time as MM:SS.S
        minutes = int(self.remaining_time // 60)
        seconds = self.remaining_time % 60

        if minutes > 0:
            time_text = f"{minutes}:{seconds:04.1f}"
        else:
            time_text = f"{seconds:.1f}"

        # Set font
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)

        # Determine text color
        if self.can_defuse:
            text_color = self.safe_color
        elif self.remaining_time <= 10.0:
            text_color = self.danger_color
        else:
            text_color = QColor(255, 255, 255)

        painter.setPen(QPen(text_color))

        # Calculate text position
        metrics = QFontMetrics(font)
        text_width = metrics.width(time_text)
        text_height = metrics.height()

        text_x = center_x - text_width // 2
        text_y = center_y + text_height // 4

        # Draw shadow
        painter.setPen(QPen(QColor(0, 0, 0, 200)))
        painter.drawText(text_x + 1, text_y + 1, time_text)

        # Draw text
        painter.setPen(QPen(text_color))
        painter.drawText(text_x, text_y, time_text)

    def _draw_defuse_kit_indicator(self, painter: QPainter, center_x: int, center_y: int):
        """Draw defuse kit indicator."""
        # Small circle below timer text
        kit_radius = 8
        kit_y = center_y + 25

        painter.setBrush(QBrush(self.defuse_color))
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(
            center_x - kit_radius,
            kit_y - kit_radius,
            kit_radius * 2,
            kit_radius * 2
        )

        # Draw "D" for defuse kit
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))

        metrics = QFontMetrics(font)
        text_width = metrics.width("D")
        text_height = metrics.height()

        painter.drawText(
            center_x - text_width // 2,
            kit_y + text_height // 4,
            "D"
        )

    def set_position(self, x: int, y: int):
        """Set overlay position."""
        self.move(x, y)

    def get_position(self) -> tuple:
        """Get current overlay position."""
        return (self.x(), self.y())

    def set_scale(self, scale: float):
        """Set overlay scale (0.5 to 2.0)."""
        scale = max(0.5, min(2.0, scale))

        self.widget_size = int(160 * scale)
        self.circle_radius = int(60 * scale)
        self.circle_thickness = int(8 * scale)
        self.font_size = int(16 * scale)

        self.setFixedSize(self.widget_size, self.widget_size)
        self.update()

    def show_overlay(self):
        """Show the overlay."""
        self.is_active = True
        self.show()

    def hide_overlay(self):
        """Hide the overlay."""
        self.is_active = False
        self.hide()

    def closeEvent(self, a0: Optional[QCloseEvent]):
        """Handle close event."""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        if a0:
            a0.accept()
