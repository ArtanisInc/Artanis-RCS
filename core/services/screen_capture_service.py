"""
Screen Capture Service for pixel detection and color analysis.
"""
import logging
import time
from typing import Tuple, Optional
import ctypes
import win32gui
import win32con
import win32api
import win32process
from PIL import Image, ImageGrab


class ScreenCaptureService:
    """Service for screen capture and color detection operations."""

    def __init__(self):
        self.logger = logging.getLogger("ScreenCaptureService")
        self.logger.info("Screen Capture Service initialized")

    def get_window_info(self, window_name: str = "Counter-Strike 2") -> Optional[Tuple[int, int, int, int]]:
        """
        Get window position and dimensions.
        
        Returns:
            Tuple of (x, y, width, height) or None if window not found
        """
        try:
            hwnd = win32gui.FindWindow(None, window_name)
            if not hwnd:
                self.logger.warning(f"Window '{window_name}' not found")
                return None
                
            # Get window rectangle
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            width = right - x
            height = bottom - y
            
            return (x, y, width, height)
            
        except Exception as e:
            self.logger.error(f"Error getting window info: {e}")
            return None

    def is_window_foreground(self, window_name: str = "Counter-Strike 2") -> bool:
        """Check if specified window is in foreground."""
        try:
            hwnd = win32gui.FindWindow(None, window_name)
            if not hwnd:
                return False
                
            foreground_hwnd = win32gui.GetForegroundWindow()
            return hwnd == foreground_hwnd
            
        except Exception as e:
            self.logger.error(f"Error checking window foreground state: {e}")
            return False

    def bring_window_to_front(self, window_name: str = "Counter-Strike 2") -> bool:
        """Bring specified window to foreground using aggressive techniques."""
        try:
            hwnd = win32gui.FindWindow(None, window_name)
            if not hwnd:
                self.logger.warning(f"Window '{window_name}' not found")
                return False
                
            self.logger.info("Using aggressive window activation techniques")
            return self._aggressive_window_activation(hwnd)
            
        except Exception as e:
            self.logger.error(f"Error bringing window to front: {e}")
            return False

    def _aggressive_window_activation(self, hwnd) -> bool:
        """
        Aggressive window activation using multiple Windows API techniques.
        This method tries every possible way to bring a window to front.
        """
        try:
            self.logger.debug("Starting aggressive window activation")
            
            # Step 1: Get current state
            current_hwnd = win32gui.GetForegroundWindow()
            self.logger.debug(f"Current foreground window: {current_hwnd}, Target: {hwnd}")
            
            # Step 2: Use AllowSetForegroundWindow to bypass restrictions
            try:
                # Get the process ID of the target window
                target_pid = win32process.GetWindowThreadProcessId(hwnd)[1]
                
                # Allow our process to set foreground window
                ctypes.windll.user32.AllowSetForegroundWindow(target_pid)
                self.logger.debug(f"AllowSetForegroundWindow called for PID: {target_pid}")
            except Exception as e:
                self.logger.debug(f"AllowSetForegroundWindow failed: {e}")
            
            # Step 3: Attach thread inputs (most important technique)
            try:
                current_thread = win32api.GetCurrentThreadId()
                target_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
                
                if current_thread != target_thread:
                    # Attach input processing
                    ctypes.windll.user32.AttachThreadInput(current_thread, target_thread, True)
                    self.logger.debug(f"Attached thread input: {current_thread} -> {target_thread}")
                    
                    # Now we should be able to set foreground
                    self._force_window_foreground(hwnd)
                    
                    # Detach
                    ctypes.windll.user32.AttachThreadInput(current_thread, target_thread, False)
                    self.logger.debug("Thread input detached")
                else:
                    self.logger.debug("Same thread, direct activation")
                    self._force_window_foreground(hwnd)
                    
            except Exception as e:
                self.logger.debug(f"Thread attachment failed: {e}")
                # Try direct activation anyway
                self._force_window_foreground(hwnd)
            
            # Step 4: Verify activation
            time.sleep(0.2)
            if self.is_window_foreground():
                self.logger.info("Aggressive window activation succeeded")
                return True
            
            # Step 5: Alternative method - simulate clicking on taskbar
            self._simulate_taskbar_click(hwnd)
            
            # Step 6: Final verification
            time.sleep(0.3)
            if self.is_window_foreground():
                self.logger.info("Alternative activation method succeeded")
                return True
            
            # Step 7: Last resort - keyboard activation
            self._keyboard_activation()
            
            time.sleep(0.2)
            if self.is_window_foreground():
                self.logger.info("Keyboard activation succeeded")
                return True
            
            self.logger.warning("All activation methods attempted, window may not be in foreground")
            # Return True anyway to continue the process
            return True
            
        except Exception as e:
            self.logger.error(f"Error in aggressive window activation: {e}")
            return False

    def _force_window_foreground(self, hwnd):
        """Direct window foreground activation."""
        try:
            # Multiple activation methods
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetActiveWindow(hwnd)
            
            # Use SetWindowPos for additional activation
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
                                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            
            self.logger.debug("Direct window activation methods applied")
            
        except Exception as e:
            self.logger.debug(f"Direct window activation failed: {e}")

    def _simulate_taskbar_click(self, hwnd):
        """Simulate clicking on the taskbar icon to activate window."""
        try:
            # Get window icon position on taskbar (this is complex but effective)
            # For now, use a simpler approach - minimize and restore
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            time.sleep(0.1)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            self.logger.debug("Taskbar simulation applied")
            
        except Exception as e:
            self.logger.debug(f"Taskbar simulation failed: {e}")

    def _keyboard_activation(self):
        """Use keyboard shortcuts to activate CS2."""
        try:
            # Try Alt+Tab multiple times to cycle to CS2
            for i in range(3):
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)  # Alt down
                win32api.keybd_event(win32con.VK_TAB, 0, 0, 0)   # Tab down
                time.sleep(0.05)
                win32api.keybd_event(win32con.VK_TAB, 0, win32con.KEYEVENTF_KEYUP, 0)  # Tab up
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)  # Alt up
                time.sleep(0.1)
                
                if self.is_window_foreground():
                    self.logger.debug(f"Keyboard activation succeeded on attempt {i+1}")
                    break
            
        except Exception as e:
            self.logger.debug(f"Keyboard activation failed: {e}")

    def capture_screen_region(self, x: int, y: int, width: int, height: int) -> Optional[Image.Image]:
        """
        Capture a specific screen region.
        
        Args:
            x, y: Top-left corner coordinates
            width, height: Region dimensions
            
        Returns:
            PIL Image or None if capture failed
        """
        try:
            # Use PIL's ImageGrab for screen capture
            bbox = (x, y, x + width, y + height)
            screenshot = ImageGrab.grab(bbox)
            return screenshot
            
        except Exception as e:
            self.logger.error(f"Error capturing screen region: {e}")
            return None

    def get_pixel_color(self, x: int, y: int) -> Optional[Tuple[int, int, int]]:
        """
        Get RGB color of pixel at specified coordinates.
        
        Args:
            x, y: Pixel coordinates
            
        Returns:
            RGB tuple (r, g, b) or None if failed
        """
        try:
            # Capture 1x1 pixel region
            screenshot = ImageGrab.grab((x, y, x + 1, y + 1))
            rgb = screenshot.getpixel((0, 0))

            # Ensure we return RGB tuple (handle RGBA if present)
            if isinstance(rgb, tuple) and len(rgb) >= 3:
                return (rgb[0], rgb[1], rgb[2])
            else:
                return None

        except Exception as e:
            self.logger.error(f"Error getting pixel color at ({x}, {y}): {e}")
            return None

    def is_color_similar(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int], tolerance: int = 20) -> bool:
        """
        Check if two colors are similar within tolerance.
        
        Args:
            color1, color2: RGB tuples to compare
            tolerance: Maximum difference per channel
            
        Returns:
            True if colors are similar
        """
        try:
            r1, g1, b1 = color1
            r2, g2, b2 = color2
            
            # Check if each channel is within tolerance
            return (abs(r1 - r2) <= tolerance and 
                   abs(g1 - g2) <= tolerance and 
                   abs(b1 - b2) <= tolerance)
                   
        except Exception as e:
            self.logger.error(f"Error comparing colors: {e}")
            return False

    def find_color_in_region(self, target_color: Tuple[int, int, int], 
                           region: Tuple[int, int, int, int], 
                           tolerance: int = 20) -> Optional[Tuple[int, int]]:
        """
        Find first occurrence of target color in region.
        
        Args:
            target_color: RGB tuple to find
            region: (x, y, width, height) region to search
            tolerance: Color matching tolerance
            
        Returns:
            (x, y) coordinates of found color or None
        """
        try:
            x, y, width, height = region
            screenshot = self.capture_screen_region(x, y, width, height)
            
            if not screenshot:
                return None
                
            # Convert to RGB if necessary
            if screenshot.mode != 'RGB':
                screenshot = screenshot.convert('RGB')
                
            # Search for color
            for py in range(height):
                for px in range(width):
                    pixel_color = screenshot.getpixel((px, py))
                    # Ensure pixel_color is a valid RGB tuple
                    if isinstance(pixel_color, tuple) and len(pixel_color) >= 3:
                        rgb_color = (pixel_color[0], pixel_color[1], pixel_color[2])
                        if self.is_color_similar(rgb_color, target_color, tolerance):
                            return (x + px, y + py)
                        
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding color in region: {e}")
            return None

    def calculate_accept_button_position(self, window_info: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """
        Calculate Accept button position based on window dimensions.
        Based on ErScripts formula: buttonX = width/2 + posX, buttonY = height/2.215 + posY
        
        Args:
            window_info: (x, y, width, height) of CS2 window
            
        Returns:
            (x, y) coordinates of Accept button
        """
        try:
            pos_x, pos_y, width, height = window_info
            
            # ErScripts formula adaptation
            button_x = int(round(width / 2.0 + pos_x))
            button_y = int(round(height / 2.215 + pos_y))
            
            return (button_x, button_y)
            
        except Exception as e:
            self.logger.error(f"Error calculating Accept button position: {e}")
            return (0, 0)

    def verify_accept_button_color(self, window_info: Tuple[int, int, int, int], 
                                  target_color: Tuple[int, int, int] = (54, 183, 82),
                                  tolerance: int = 20) -> bool:
        """
        Verify if Accept button shows the expected green color.
        
        Args:
            window_info: CS2 window information
            target_color: Expected RGB color of Accept button
            tolerance: Color matching tolerance
            
        Returns:
            True if Accept button color matches
        """
        try:
            button_x, button_y = self.calculate_accept_button_position(window_info)
            current_color = self.get_pixel_color(button_x, button_y)
            
            if not current_color:
                return False
                
            is_similar = self.is_color_similar(current_color, target_color, tolerance)
            
            if is_similar:
                self.logger.debug(f"Accept button color verified at ({button_x}, {button_y}): {current_color}")
            else:
                self.logger.debug(f"Accept button color mismatch at ({button_x}, {button_y}): {current_color} vs {target_color}")
                
            return is_similar
            
        except Exception as e:
            self.logger.error(f"Error verifying Accept button color: {e}")
            return False

    def get_status(self) -> dict:
        """Get current service status."""
        cs2_window_info = self.get_window_info()
        return {
            "cs2_window_found": cs2_window_info is not None,
            "cs2_window_info": cs2_window_info,
            "cs2_window_foreground": self.is_window_foreground(),
            "service_ready": True
        }
