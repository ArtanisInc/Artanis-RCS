"""
Views package for user interface views and tabs.
"""

from .main_window import MainWindow, ControlPanel
from .config_tab import ConfigTab
from .visualization_tab import VisualizationTab
from .styles import (
    ColorPalette,
    Spacing,
    BorderRadius,
    Typography,
    ComponentStyles,
    MAIN_WINDOW_STYLES,
    CONFIG_TAB_STYLES,
    VISUALIZATION_TAB_STYLES
)

__all__ = [
    'MainWindow',
    'ControlPanel',
    'ConfigTab',
    'VisualizationTab',
    'ColorPalette',
    'Spacing',
    'BorderRadius',
    'Typography',
    'ComponentStyles',
    'MAIN_WINDOW_STYLES',
    'CONFIG_TAB_STYLES',
    'VISUALIZATION_TAB_STYLES'
]
