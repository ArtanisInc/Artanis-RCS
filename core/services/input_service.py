"""
System input management service using Windows SendInput API.
"""
import ctypes
import logging
import time
from typing import Dict, Optional

import win32api
import win32con
from ctypes import wintypes


class WindowsInputAPI:
    """Windows API constants and structures for SendInput."""

    # Mouse event flags
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040

    # Input types
    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1

    # Keyboard event flags
    KEYEVENTF_KEYUP = 0x0002


class KeyMapping:
    """Virtual key code mappings."""

    SPECIAL_KEYS = {
        "INSERT": win32con.VK_INSERT,
        "HOME": win32con.VK_HOME,
        "DELETE": win32con.VK_DELETE,
        "END": win32con.VK_END,
        "PGUP": win32con.VK_PRIOR,
        "PGDN": win32con.VK_NEXT,
        "ESCAPE": win32con.VK_ESCAPE,
        "LBUTTON": win32con.VK_LBUTTON,
        "RBUTTON": win32con.VK_RBUTTON,
        "MBUTTON": win32con.VK_MBUTTON,
        "XBUTTON1": win32con.VK_XBUTTON1,
        "XBUTTON2": win32con.VK_XBUTTON2,
        "CTRL": win32con.VK_CONTROL,
        "ALT": win32con.VK_MENU,
        "SHIFT": win32con.VK_SHIFT,
        "SPACE": win32con.VK_SPACE,
        "ENTER": win32con.VK_RETURN,
        "TAB": win32con.VK_TAB,
        "CAPSLOCK": win32con.VK_CAPITAL,
        "NUMLOCK": win32con.VK_NUMLOCK,
        "SCROLLLOCK": win32con.VK_SCROLL,
        "PAUSE": win32con.VK_PAUSE,
        "PRINTSCREEN": win32con.VK_SNAPSHOT,
        "LWIN": win32con.VK_LWIN,
        "RWIN": win32con.VK_RWIN,
        "APPS": win32con.VK_APPS,
        "BACKSPACE": win32con.VK_BACK,
        "LEFT": win32con.VK_LEFT,
        "UP": win32con.VK_UP,
        "RIGHT": win32con.VK_RIGHT,
        "DOWN": win32con.VK_DOWN,
    }

    FUNCTION_KEYS = {
        f"F{i}": getattr(win32con, f"VK_F{i}")
        for i in range(1, 13)
    }

    NUMPAD_KEYS = {
        f"NUMPAD{i}": getattr(win32con, f"VK_NUMPAD{i}")
        for i in range(10)
    }

    NUMPAD_OPERATORS = {
        "MULTIPLY": win32con.VK_MULTIPLY,
        "ADD": win32con.VK_ADD,
        "SEPARATOR": win32con.VK_SEPARATOR,
        "SUBTRACT": win32con.VK_SUBTRACT,
        "DECIMAL": win32con.VK_DECIMAL,
        "DIVIDE": win32con.VK_DIVIDE,
    }

    PUNCTUATION = {
        ";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD,
        ".": 0xBE, "/": 0xBF, "`": 0xC0, "[": 0xDB,
        "\\": 0xDC, "]": 0xDD, "'": 0xDE,
    }

    @classmethod
    def get_all_mappings(cls) -> Dict[str, int]:
        """Get complete key mapping dictionary."""
        mappings = {}
        mappings.update(cls.SPECIAL_KEYS)
        mappings.update(cls.FUNCTION_KEYS)
        mappings.update(cls.NUMPAD_KEYS)
        mappings.update(cls.NUMPAD_OPERATORS)
        mappings.update(cls.PUNCTUATION)

        # Add alphabet
        for i in range(ord('A'), ord('Z') + 1):
            mappings[chr(i)] = i

        return mappings


# Windows API structures
PUL = ctypes.POINTER(ctypes.c_ulong)


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL)
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL)
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT)
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION)
    ]


class InputService:
    """Low-level input management service."""

    def __init__(self):
        self.logger = logging.getLogger("InputService")
        self._initialize_api()
        self._key_mappings = KeyMapping.get_all_mappings()
        self._last_key_states = {}
        self.logger.debug("Input service initialized")

    def _initialize_api(self) -> None:
        """Initialize Windows API functions."""
        try:
            self.user32 = ctypes.WinDLL('user32', use_last_error=True)
            self.user32.SendInput.argtypes = (
                wintypes.UINT,
                ctypes.POINTER(INPUT),
                ctypes.c_int
            )
            self.user32.SendInput.restype = wintypes.UINT
            self.logger.debug("Windows API initialized")
        except Exception as e:
            self.logger.error("API initialization failed: %s", e)
            raise

    def mouse_move(self, dx: int, dy: int) -> None:
        """Move mouse relative to current position."""
        try:
            mouse_input = MOUSEINPUT(
                dx=dx, dy=dy, mouseData=0,
                dwFlags=WindowsInputAPI.MOUSEEVENTF_MOVE,
                time=0, dwExtraInfo=None
            )
            input_obj = INPUT(
                type=WindowsInputAPI.INPUT_MOUSE,
                union=INPUT_UNION(mi=mouse_input)
            )
            self.user32.SendInput(
                1, ctypes.byref(input_obj), ctypes.sizeof(INPUT))

            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("Mouse moved: dx=%s, dy=%s", dx, dy)

        except Exception as e:
            self.logger.error("Mouse move failed (dx=%s, dy=%s): %s", dx, dy, e)

    def mouse_click(self, button: str = "LEFT") -> None:
        """Simulate mouse click."""
        button_flags = {
            "LEFT": (
                WindowsInputAPI.MOUSEEVENTF_LEFTDOWN,
                WindowsInputAPI.MOUSEEVENTF_LEFTUP),
            "RIGHT": (
                WindowsInputAPI.MOUSEEVENTF_RIGHTDOWN,
                WindowsInputAPI.MOUSEEVENTF_RIGHTUP),
            "MIDDLE": (
                WindowsInputAPI.MOUSEEVENTF_MIDDLEDOWN,
                WindowsInputAPI.MOUSEEVENTF_MIDDLEUP),
        }

        if button not in button_flags:
            self.logger.warning("Unsupported mouse button: %s", button)
            return

        down_flag, up_flag = button_flags[button]

        try:
            inputs = (INPUT * 2)()

            # Button press
            inputs[0].type = WindowsInputAPI.INPUT_MOUSE
            inputs[0].union.mi = MOUSEINPUT(
                dx=0, dy=0, mouseData=0, dwFlags=down_flag,
                time=0, dwExtraInfo=None
            )

            # Button release
            inputs[1].type = WindowsInputAPI.INPUT_MOUSE
            inputs[1].union.mi = MOUSEINPUT(
                dx=0, dy=0, mouseData=0, dwFlags=up_flag,
                time=0, dwExtraInfo=None
            )

            self.user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
            self.logger.debug("Mouse clicked: %s", button)

        except Exception as e:
            self.logger.error("Mouse click failed (%s): %s", button, e)

    def key_down(self, vk_code: int) -> None:
        """Press key down."""
        try:
            key_input = KEYBDINPUT(
                wVk=vk_code, wScan=0, dwFlags=0,
                time=0, dwExtraInfo=None
            )
            input_obj = INPUT(
                type=WindowsInputAPI.INPUT_KEYBOARD,
                union=INPUT_UNION(ki=key_input)
            )
            self.user32.SendInput(
                1, ctypes.byref(input_obj), ctypes.sizeof(INPUT))
            self.logger.debug("Key pressed: VK_%s", vk_code)
        except Exception as e:
            self.logger.error("Key down failed (VK_%s): %s", vk_code, e)

    def key_up(self, vk_code: int) -> None:
        """Release key."""
        try:
            key_input = KEYBDINPUT(
                wVk=vk_code, wScan=0, dwFlags=WindowsInputAPI.KEYEVENTF_KEYUP,
                time=0, dwExtraInfo=None
            )
            input_obj = INPUT(
                type=WindowsInputAPI.INPUT_KEYBOARD,
                union=INPUT_UNION(ki=key_input)
            )
            self.user32.SendInput(
                1, ctypes.byref(input_obj), ctypes.sizeof(INPUT))
            self.logger.debug("Key released: VK_%s", vk_code)
        except Exception as e:
            self.logger.error("Key up failed (VK_%s): %s", vk_code, e)

    def key_press(self, vk_code: int, delay: float = 0.05) -> None:
        """Press and release key with delay."""
        self.key_down(vk_code)
        time.sleep(delay)
        self.key_up(vk_code)

    def is_key_pressed(self, vk_code: int) -> bool:
        """Check if key is currently pressed."""
        try:
            state = win32api.GetAsyncKeyState(vk_code)
            is_pressed = bool(state & 0x8000)

            # Log only state changes to avoid spam
            if self._last_key_states.get(vk_code) != is_pressed:
                if self.logger.isEnabledFor(logging.DEBUG):
                    status = "pressed" if is_pressed else "released"
                    self.logger.debug("Key VK_%s: %s", vk_code, status)
                self._last_key_states[vk_code] = is_pressed

            return is_pressed
        except Exception as e:
            self.logger.error("Key state check failed (VK_%s): %s", vk_code, e)
            return False

    def get_key_code(self, key_name: str) -> Optional[int]:
        """Get virtual key code from name."""
        if "+" in key_name:
            # For combinations, return the last key
            parts = key_name.split("+")
            return self._key_mappings.get(parts[-1].strip().upper())
        return self._key_mappings.get(key_name.upper())
