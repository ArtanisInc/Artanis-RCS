"""
Bomb Timer Overlay Widget for CS2 bomb countdown display.
"""

import logging
import math
import time
from typing import Optional

import qtawesome as qta
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QCloseEvent,
    QColor,
    QFont,
    QFontMetrics,
    QPaintEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget


class BombTimerOverlay(QWidget):
    """Overlay widget displaying bomb countdown timer with critical-state animation."""

    timer_expired = Signal()
    defuse_alert = Signal(bool)

    FINISH_STATE_DISPLAY_SECONDS = 1.2
    CRITICAL_THRESHOLD_SECONDS = 10.0

    def __init__(self, config_service=None, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger("BombTimerOverlay")
        self.config_service = config_service

        self.remaining_time = 0.0
        self.max_time = 40.0
        self.has_defuse_kit = False
        self.can_defuse = False
        self.state = "idle"

        self.widget_size = 160
        self.circle_radius = 60
        self.circle_thickness = 8
        self.font_size = 16
        self.scale_factor = 1.0

        self.safe_color = QColor(46, 204, 113)
        self.warning_color = QColor(241, 196, 15)
        self.danger_color = QColor(231, 76, 60)
        self.defuse_color = QColor(52, 152, 219)
        self.background_color = QColor(44, 62, 80)

        self._finish_state_deadline = 0.0
        self._flash_boost_until = 0.0
        self._last_critical = False

        self._setup_ui()
        self._setup_animation_timer()
        self._apply_saved_settings()

        self.hide()
        self.logger.debug("Bomb timer overlay initialized")

    def _setup_ui(self):
        """Setup the user interface."""
        self.setFixedSize(self.widget_size, self.widget_size)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent;")
        self._move_to_default_position()

    def _setup_animation_timer(self):
        """Create an on-demand animation timer."""
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(33)
        self.animation_timer.timeout.connect(self._on_animation_frame)

    def _apply_saved_settings(self):
        """Apply persisted overlay scale and position if present."""
        bomb_timer_config = {}
        if self.config_service:
            bomb_timer_config = self.config_service.config.get("bomb_timer", {})

        self.set_scale(bomb_timer_config.get("scale", 1.0), persist=False)

        x = bomb_timer_config.get("x")
        y = bomb_timer_config.get("y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)
        else:
            self._move_to_default_position()

    def _move_to_default_position(self):
        """Position the overlay near the top-right corner of the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x_pos = screen_geometry.right() - self.widget_size - 50
            y_pos = screen_geometry.top() + 50
            self.move(x_pos, y_pos)

    def _persist_overlay_config(self):
        """Persist overlay position and scale to config."""
        if not self.config_service:
            return

        bomb_timer_config = self.config_service.config.get("bomb_timer", {})
        if not isinstance(bomb_timer_config, dict):
            bomb_timer_config = {}

        bomb_timer_config.update(
            {
                "scale": round(self.scale_factor, 2),
                "x": int(self.x()),
                "y": int(self.y()),
            }
        )
        self.config_service.config["bomb_timer"] = bomb_timer_config
        if not self.config_service.save_config():
            self.logger.warning("Failed to persist bomb timer overlay configuration")

    def _is_finished_state(self) -> bool:
        return self.state in {"defused", "exploded"}

    def _should_draw(self) -> bool:
        if self.state == "planted":
            return self.remaining_time > 0.0
        return self._is_finished_state()

    def _is_critical_phase(self) -> bool:
        return self.state == "planted" and (
            self.remaining_time <= self.CRITICAL_THRESHOLD_SECONDS or not self.can_defuse
        )

    def _current_pulse_strength(self) -> float:
        """Return animation intensity between 0 and 1."""
        phase = time.monotonic()

        if self._is_finished_state():
            speed = 8.0 if self.state == "defused" else 12.0
            return 0.5 + 0.5 * math.sin(phase * speed)

        if not self._is_critical_phase():
            return 0.0

        return 0.5 + 0.5 * math.sin(phase * 10.0)

    def _flash_boost(self) -> float:
        remaining = self._flash_boost_until - time.monotonic()
        if remaining <= 0:
            return 0.0
        return min(1.0, remaining / 0.6)

    def _sync_animation_timer(self):
        """Start/stop the animation timer only when it is actually needed."""
        should_animate = self._is_finished_state() or self._is_critical_phase()
        if should_animate and not self.animation_timer.isActive():
            self.animation_timer.start()
        elif not should_animate and self.animation_timer.isActive():
            self.animation_timer.stop()

    def _on_animation_frame(self):
        """Run transient animation frames while critical or showing a terminal state."""
        if self._is_finished_state() and time.monotonic() >= self._finish_state_deadline:
            self.hide_overlay()
            self.state = "idle"
            self._sync_animation_timer()
            return

        if not self._should_draw():
            self.hide_overlay()
            self._sync_animation_timer()
            return

        self.update()

    def update_bomb_state(
        self,
        remaining_time: float,
        has_defuse_kit: bool,
        can_defuse: bool,
        state: str = "planted",
    ):
        """Update bomb timer state from the service layer."""
        state = state or "planted"

        was_critical = self._is_critical_phase()
        previous_can_defuse = self.can_defuse

        self.remaining_time = max(0.0, remaining_time)
        self.has_defuse_kit = has_defuse_kit
        self.can_defuse = can_defuse
        self.state = state

        if state == "planted":
            if not self.isVisible():
                self.show()
            self.raise_()
        elif self._is_finished_state():
            self.show()
            self.raise_()
            self._finish_state_deadline = (
                time.monotonic() + self.FINISH_STATE_DISPLAY_SECONDS
            )
            self._flash_boost_until = max(
                self._flash_boost_until, time.monotonic() + 0.8
            )
        else:
            self.hide_overlay()
            self._sync_animation_timer()
            return

        is_critical = self._is_critical_phase()
        if (not was_critical and is_critical) or (
            previous_can_defuse and not self.can_defuse
        ):
            self._flash_boost_until = max(
                self._flash_boost_until, time.monotonic() + 0.6
            )

        self._last_critical = is_critical
        self._sync_animation_timer()
        self.update()

    def paintEvent(self, event: Optional[QPaintEvent]):
        """Paint the bomb timer overlay."""
        if not self._should_draw():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() // 2
        center_y = self.height() // 2

        pulse_strength = self._current_pulse_strength()
        flash_boost = self._flash_boost()

        self._draw_background_circle(painter, center_x, center_y, pulse_strength, flash_boost)

        if self.state == "planted":
            self._draw_progress_arc(
                painter, center_x, center_y, pulse_strength, flash_boost
            )
            self._draw_timer_text(painter, center_x, center_y)
            if self.has_defuse_kit:
                self._draw_defuse_kit_indicator(painter, center_x, center_y)
        else:
            self._draw_result_ring(
                painter, center_x, center_y, pulse_strength, flash_boost
            )
            self._draw_result_text(painter, center_x, center_y)

        if event:
            event.accept()

    def _draw_background_circle(
        self,
        painter: QPainter,
        center_x: int,
        center_y: int,
        pulse_strength: float,
        flash_boost: float,
    ):
        """Draw the animated background circle."""
        radius_boost = int(4 * pulse_strength)
        radius = self.circle_radius + 10 + radius_boost
        alpha = 120 + int(55 * pulse_strength) + int(45 * flash_boost)
        border_alpha = 180 + int(40 * pulse_strength) + int(35 * flash_boost)

        painter.setBrush(QBrush(QColor(0, 0, 0, min(255, alpha))))
        painter.setPen(QPen(QColor(120, 120, 120, min(255, border_alpha)), 2))
        painter.drawEllipse(
            center_x - radius,
            center_y - radius,
            radius * 2,
            radius * 2,
        )

    def _determine_main_color(self) -> QColor:
        """Pick the current highlight color from the countdown state."""
        if self.state == "defused":
            return self.defuse_color
        if self.state == "exploded":
            return self.danger_color
        if not self.can_defuse:
            return self.danger_color
        if self.remaining_time <= self.CRITICAL_THRESHOLD_SECONDS:
            return self.warning_color
        return self.safe_color

    def _draw_progress_arc(
        self,
        painter: QPainter,
        center_x: int,
        center_y: int,
        pulse_strength: float,
        flash_boost: float,
    ):
        """Draw the circular progress arc."""
        progress = max(0.0, min(1.0, self.remaining_time / self.max_time))
        color = self._determine_main_color()

        dynamic_radius = self.circle_radius + int(2 * pulse_strength)
        dynamic_thickness = self.circle_thickness + int(2 * pulse_strength) + int(
            2 * flash_boost
        )

        pen = QPen(color, dynamic_thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        start_angle = -90 * 16
        span_angle = int(-360 * 16 * progress)

        painter.drawArc(
            center_x - dynamic_radius,
            center_y - dynamic_radius,
            dynamic_radius * 2,
            dynamic_radius * 2,
            start_angle,
            span_angle,
        )

        if progress < 1.0:
            pen_bg = QPen(QColor(255, 255, 255, 55), dynamic_thickness)
            pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_bg)
            painter.drawArc(
                center_x - dynamic_radius,
                center_y - dynamic_radius,
                dynamic_radius * 2,
                dynamic_radius * 2,
                start_angle + span_angle,
                -360 * 16 - span_angle,
            )

    def _draw_timer_text(self, painter: QPainter, center_x: int, center_y: int):
        """Draw only the countdown timer in the center."""
        minutes = int(self.remaining_time // 60)
        seconds = self.remaining_time % 60
        time_text = f"{minutes}:{seconds:04.1f}" if minutes > 0 else f"{seconds:.1f}"

        font = QFont("Arial", self.font_size, QFont.Weight.Bold)
        painter.setFont(font)
        text_color = self._determine_main_color()

        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(time_text)
        text_height = metrics.height()
        text_x = center_x - text_width // 2
        text_y = center_y + text_height // 6

        painter.setPen(QPen(QColor(0, 0, 0, 210)))
        painter.drawText(text_x + 1, text_y + 1, time_text)
        painter.setPen(QPen(text_color))
        painter.drawText(text_x, text_y, time_text)

    def _draw_result_ring(
        self,
        painter: QPainter,
        center_x: int,
        center_y: int,
        pulse_strength: float,
        flash_boost: float,
    ):
        """Draw a full animated ring for terminal states."""
        color = self._determine_main_color()
        radius = self.circle_radius + int(3 * pulse_strength)
        thickness = self.circle_thickness + 2 + int(3 * flash_boost)
        pen = QPen(color, thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(
            center_x - radius,
            center_y - radius,
            radius * 2,
            radius * 2,
        )

    def _draw_result_text(self, painter: QPainter, center_x: int, center_y: int):
        """Draw terminal-state text only for defused/exploded states."""
        result_text = "DEFUSED" if self.state == "defused" else "BOOM"
        font = QFont("Arial", max(14, self.font_size), QFont.Weight.Bold)
        painter.setFont(font)

        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(result_text)
        text_height = metrics.height()
        text_x = center_x - text_width // 2
        text_y = center_y + text_height // 6

        color = self._determine_main_color()
        painter.setPen(QPen(QColor(0, 0, 0, 210)))
        painter.drawText(text_x + 1, text_y + 1, result_text)
        painter.setPen(QPen(color))
        painter.drawText(text_x, text_y, result_text)

    def _draw_defuse_kit_indicator(self, painter: QPainter, center_x: int, center_y: int):
        """Draw a font-based pliers icon for the defuse kit."""
        icon_size = max(18, int(24 * self.scale_factor))
        icon_x = center_x - icon_size // 2
        icon_y = center_y + int(self.circle_radius * 0.25)

        shadow_icon = qta.icon("mdi6.pliers", color=QColor(0, 0, 0, 170))
        shadow_pixmap = shadow_icon.pixmap(icon_size, icon_size)
        painter.drawPixmap(icon_x + 1, icon_y + 1, shadow_pixmap)

        icon = qta.icon("mdi6.pliers", color=self.defuse_color)
        pixmap = icon.pixmap(icon_size, icon_size)
        painter.drawPixmap(icon_x, icon_y, pixmap)

    def set_position(self, x: int, y: int, persist: bool = True):
        """Set overlay position."""
        self.move(x, y)
        if persist:
            self._persist_overlay_config()

    def get_position(self) -> tuple[int, int]:
        """Get current overlay position."""
        return (self.x(), self.y())

    def set_scale(self, scale: float, persist: bool = True):
        """Set overlay scale (0.5 to 2.0)."""
        scale = max(0.5, min(2.0, float(scale)))
        if abs(scale - self.scale_factor) < 0.001:
            return

        center = self.frameGeometry().center()
        self.scale_factor = scale
        self.widget_size = int(160 * scale)
        self.circle_radius = int(60 * scale)
        self.circle_thickness = max(6, int(8 * scale))
        self.font_size = max(12, int(16 * scale))

        self.setFixedSize(self.widget_size, self.widget_size)
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
        self.update()

        if persist:
            self._persist_overlay_config()

    def show_overlay(self):
        """Show the overlay."""
        self.state = "planted"
        self.show()
        self._sync_animation_timer()

    def hide_overlay(self):
        """Hide the overlay and stop active animation."""
        self.hide()
        self.remaining_time = 0.0
        self._finish_state_deadline = 0.0
        self._sync_animation_timer()

    def closeEvent(self, event: Optional[QCloseEvent]):
        """Handle close event."""
        if hasattr(self, "animation_timer"):
            self.animation_timer.stop()
        if event:
            event.accept()
