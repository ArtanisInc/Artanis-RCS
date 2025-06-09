"""
Centralized CSS styles for the user interface.
Qt-compatible styling with design system constants.
"""


class ColorPalette:
    """Color palette constants for consistent theming."""

    # Primary colors
    PRIMARY = "#2196F3"
    PRIMARY_DARK = "#1976D2"
    PRIMARY_DARKER = "#0D47A1"

    # Semantic colors
    SUCCESS = "#4CAF50"
    SUCCESS_DARK = "#45a049"
    SUCCESS_DARKER = "#388e3c"

    WARNING = "#FF9800"
    WARNING_DARK = "#F57C00"

    DANGER = "#f44336"
    DANGER_DARK = "#da190b"

    ACCENT = "#9C27B0"
    ACCENT_DARK = "#6A1B9A"

    # Neutral scale
    NEUTRAL_50 = "#fafafa"
    NEUTRAL_100 = "#f5f5f5"
    NEUTRAL_200 = "#eeeeee"
    NEUTRAL_300 = "#e0e0e0"
    NEUTRAL_400 = "#cccccc"
    NEUTRAL_500 = "#999999"
    NEUTRAL_600 = "#666666"
    NEUTRAL_700 = "#444444"
    NEUTRAL_800 = "#333333"
    NEUTRAL_900 = "#222222"


class Spacing:
    """Spacing constants for consistent layout."""

    XS = "2px"
    SM = "4px"
    MD = "6px"
    LG = "8px"
    XL = "12px"
    XXL = "16px"


class BorderRadius:
    """Border radius constants."""

    SM = "3px"
    MD = "4px"
    LG = "6px"
    XL = "8px"


class Typography:
    """Typography constants."""

    FONT_FAMILY = "Arial"
    SIZE_SM = "9px"
    SIZE_MD = "11px"
    SIZE_LG = "13px"
    WEIGHT_NORMAL = "300"
    WEIGHT_BOLD = "600"


class ComponentStyles:
    """Pre-built component style generators."""

    @staticmethod
    def button_primary() -> str:
        """Primary button style."""
        return f"""
            QPushButton {{
                background-color: {ColorPalette.PRIMARY};
                color: white;
                border: none;
                border-radius: {BorderRadius.MD};
                padding: {Spacing.MD} {Spacing.XL};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ColorPalette.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {ColorPalette.PRIMARY_DARKER};
            }}
            QPushButton:disabled {{
                background-color: {ColorPalette.NEUTRAL_400};
                color: {ColorPalette.NEUTRAL_600};
            }}
        """

    @staticmethod
    def button_success() -> str:
        """Success button style."""
        return f"""
            QPushButton {{
                background-color: {ColorPalette.SUCCESS};
                color: white;
                border: none;
                border-radius: {BorderRadius.MD};
                padding: {Spacing.MD} {Spacing.XL};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ColorPalette.SUCCESS_DARK};
            }}
            QPushButton:pressed {{
                background-color: {ColorPalette.SUCCESS_DARKER};
            }}
        """

    @staticmethod
    def button_danger() -> str:
        """Danger button style."""
        return f"""
            QPushButton {{
                background-color: {ColorPalette.DANGER};
                color: white;
                border: none;
                border-radius: {BorderRadius.MD};
                padding: {Spacing.MD} {Spacing.XL};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ColorPalette.DANGER_DARK};
            }}
        """

    @staticmethod
    def input_field() -> str:
        """Standard input field style."""
        return f"""
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
                border: 2px solid {ColorPalette.NEUTRAL_400};
                border-radius: {BorderRadius.MD};
                padding: {Spacing.SM} {Spacing.LG};
                background-color: white;
            }}
            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
                border: 2px solid {ColorPalette.PRIMARY};
            }}
        """

    @staticmethod
    def checkbox() -> str:
        """Checkbox style."""
        return f"""
            QCheckBox {{
                color: {ColorPalette.NEUTRAL_800};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {ColorPalette.NEUTRAL_400};
                border-radius: {BorderRadius.SM};
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                background-color: {ColorPalette.PRIMARY};
                border-color: {ColorPalette.PRIMARY};
            }}
        """

    @staticmethod
    def group_box() -> str:
        """Group box style."""
        return f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {ColorPalette.NEUTRAL_400};
                border-radius: {BorderRadius.LG};
                margin-top: {Spacing.LG};
                padding-top: {Spacing.MD};
                background-color: white;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.LG};
                padding: 0 {Spacing.MD} 0 {Spacing.MD};
                color: {ColorPalette.NEUTRAL_800};
            }}
        """


# Main window styles
MAIN_WINDOW_STYLES = f"""
QMainWindow {{
    background-color: {ColorPalette.NEUTRAL_100};
}}

{ComponentStyles.group_box()}

/* Tab system */
QTabWidget::pane {{
    border: 1px solid {ColorPalette.NEUTRAL_400};
    top: -1px;
    background: white;
    border-radius: {BorderRadius.LG};
}}

QTabBar::tab {{
    background: {ColorPalette.NEUTRAL_100};
    border: 1px solid {ColorPalette.NEUTRAL_300};
    border-bottom: none;
    border-top-left-radius: {BorderRadius.XL};
    border-top-right-radius: {BorderRadius.XL};
    padding: {Spacing.LG} {Spacing.XXL};
    margin-right: {Spacing.XS};
    font-weight: {Typography.WEIGHT_NORMAL};
    color: {ColorPalette.NEUTRAL_700};
    min-width: 130px;
}}

QTabBar::tab:first {{
    margin-left: {Spacing.XL};
}}

QTabBar::tab:selected {{
    background: white;
    color: black;
    border-color: {ColorPalette.NEUTRAL_500};
    font-weight: {Typography.WEIGHT_BOLD};
}}

QTabBar::tab:hover:!selected {{
    background: {ColorPalette.NEUTRAL_200};
    color: {ColorPalette.NEUTRAL_900};
}}

QFrame[frameShape="4"] {{
    color: {ColorPalette.NEUTRAL_400};
}}
"""

# Configuration tab styles
CONFIG_TAB_STYLES = f"""
{ComponentStyles.group_box()}

QFrame {{
    background-color: white;
    border: 1px solid {ColorPalette.NEUTRAL_300};
    border-radius: {BorderRadius.MD};
    margin: {Spacing.XS};
}}

{ComponentStyles.button_primary()}

/* Specialized buttons with object names */
QPushButton[objectName="assign_weapon_key_button"] {{
    background-color: {ColorPalette.SUCCESS};
    color: white;
    border: none;
    border-radius: {BorderRadius.SM};
    padding: {Spacing.SM} {Spacing.LG};
    font-size: {Typography.SIZE_SM};
    font-weight: bold;
}}

QPushButton[objectName="assign_weapon_key_button"]:hover {{
    background-color: {ColorPalette.SUCCESS_DARK};
}}

QPushButton[objectName="remove_weapon_key_button"] {{
    background-color: {ColorPalette.DANGER};
    color: white;
    border: none;
    border-radius: {BorderRadius.SM};
    padding: {Spacing.SM} {Spacing.LG};
    font-size: {Typography.SIZE_SM};
    font-weight: bold;
}}

QPushButton[objectName="remove_weapon_key_button"]:hover {{
    background-color: {ColorPalette.DANGER_DARK};
}}

{ComponentStyles.input_field()}

/* Specialized combo boxes */
QComboBox[objectName="weapon_hotkey_combo"] {{
    border: 2px solid {ColorPalette.SUCCESS};
    border-radius: {BorderRadius.MD};
    padding: {Spacing.SM} {Spacing.LG};
    background-color: #f8fff8;
}}

QComboBox[objectName="weapon_hotkey_combo"]:focus {{
    border: 2px solid #2E7D32;
}}

QComboBox[objectName="key_hotkey_combo"] {{
    border: 2px solid {ColorPalette.WARNING};
    border-radius: {BorderRadius.MD};
    padding: {Spacing.SM} {Spacing.LG};
    background-color: #fff8f0;
}}

QComboBox[objectName="key_hotkey_combo"]:focus {{
    border: 2px solid {ColorPalette.WARNING_DARK};
}}

QComboBox[objectName="input_souris_combo"] {{
    border: 2px solid {ColorPalette.ACCENT};
    border-radius: {BorderRadius.MD};
    padding: {Spacing.SM} {Spacing.LG};
    background-color: #fdf7ff;
}}

QComboBox[objectName="input_souris_combo"]:focus {{
    border: 2px solid {ColorPalette.ACCENT_DARK};
}}

{ComponentStyles.checkbox()}

/* Scrollbars */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: {ColorPalette.NEUTRAL_100};
    width: 14px;
    border-radius: 7px;
}}

QScrollBar::handle:vertical {{
    background-color: {ColorPalette.NEUTRAL_400};
    border-radius: 7px;
    min-height: 25px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {ColorPalette.NEUTRAL_500};
}}

/* Section titles */
QLabel[objectName="section_title"] {{
    font-weight: bold;
    color: {ColorPalette.PRIMARY};
    font-size: {Typography.SIZE_MD};
    border-bottom: 1px solid {ColorPalette.PRIMARY};
    padding-bottom: {Spacing.XS};
    margin-bottom: {Spacing.SM};
}}

QLabel[objectName="section_title_header"] {{
    font-weight: bold;
    font-size: {Typography.SIZE_LG};
    color: {ColorPalette.PRIMARY};
    border-bottom: 1px solid {ColorPalette.PRIMARY};
    padding-bottom: {Spacing.XS};
    margin-bottom: {Spacing.SM};
}}
"""

# Visualization tab styles
VISUALIZATION_TAB_STYLES = f"""
{ComponentStyles.group_box()}

{ComponentStyles.button_success()}

QCheckBox {{
    font-weight: bold;
    color: {ColorPalette.NEUTRAL_800};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {ColorPalette.NEUTRAL_400};
    border-radius: {BorderRadius.SM};
    background-color: white;
}}

QCheckBox::indicator:checked {{
    background-color: {ColorPalette.SUCCESS};
    border-color: {ColorPalette.SUCCESS};
}}

QComboBox {{
    border: 2px solid {ColorPalette.NEUTRAL_400};
    border-radius: {BorderRadius.MD};
    padding: {Spacing.SM} {Spacing.LG};
    background-color: white;
}}

QComboBox:focus {{
    border: 2px solid {ColorPalette.SUCCESS};
}}
"""
