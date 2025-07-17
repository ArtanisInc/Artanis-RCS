"""
Screen Capture Service for pixel detection and color analysis.
"""
import logging
import time
from typing import Tuple, Optional, Dict, Any
import win32gui
import win32con
import numpy as np
import dxcam


class ScreenCaptureService:
    """Service for screen capture and color detection operations."""

    def __init__(self):
        self.logger = logging.getLogger("ScreenCaptureService")

        self.camera = dxcam.create(
            device_idx=0,
            output_idx=0,
            output_color="RGB",
            max_buffer_len=2
        )

        if self.camera is None:
            raise RuntimeError("Failed to initialize DXcam. Ensure DirectX is available and display drivers are up to date.")

        self.frame_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_ms = 100
        self.max_cache_size = 5
        self.last_cleanup_time = 0

        self.capture_count = 0
        self.cache_hits = 0

        self.common_regions = {}

        self.logger.info("Screen Capture Service initialized")

    def _cleanup_cache(self):
        """Cache cleanup - only run periodically."""
        current_time = time.time() * 1000

        if current_time - self.last_cleanup_time < 500:
            return

        self.last_cleanup_time = current_time

        expired_keys = [
            key for key, data in self.frame_cache.items()
            if current_time - data['timestamp'] > self.cache_ttl_ms
        ]

        for key in expired_keys:
            del self.frame_cache[key]

        if len(self.frame_cache) > self.max_cache_size:
            sorted_items = sorted(self.frame_cache.items(), key=lambda x: x[1]['timestamp'])
            for key, _ in sorted_items[:-self.max_cache_size]:
                del self.frame_cache[key]

    def _get_region_key(self, region: Tuple[int, int, int, int]) -> str:
        """Generates a unique key for a given region."""
        return f"{region[0]}_{region[1]}_{region[2]}_{region[3]}"

    def get_window_info(self, window_name: str = "Counter-Strike 2") -> Optional[Tuple[int, int, int, int]]:
        """Get window position and dimensions."""
        try:
            hwnd = win32gui.FindWindow(None, window_name)
            if not hwnd:
                self.logger.warning(f"Window '{window_name}' not found")
                return None

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
        """Bring specified window to foreground."""
        try:
            hwnd = win32gui.FindWindow(None, window_name)
            if not hwnd:
                self.logger.warning(f"Window '{window_name}' not found")
                return False

            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            time.sleep(0.1)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)

            return self.is_window_foreground()

        except Exception as e:
            self.logger.error(f"Error bringing window to front: {e}")
            return False

    def capture_region(self, region: Tuple[int, int, int, int], use_cache: bool = True) -> Optional[np.ndarray]:
        """
        Captures a screen region with aggressive caching.
        This is the primary screen capture method.
        """
        cache_key = self._get_region_key(region)
        current_time = time.time() * 1000

        if use_cache and cache_key in self.frame_cache:
            cache_data = self.frame_cache[cache_key]
            if current_time - cache_data['timestamp'] <= self.cache_ttl_ms:
                self.cache_hits += 1
                return cache_data['frame']

        try:
            x, y, width, height = region

            frame = self.camera.grab(region=(x, y, x + width, y + height))
            self.capture_count += 1

            if frame is not None:
                if use_cache:
                    self.frame_cache[cache_key] = {
                        'frame': frame,
                        'timestamp': current_time
                    }

                    if self.capture_count % 20 == 0:
                        self._cleanup_cache()

                return frame
            else:
                self.logger.warning(f"DXcam failed to capture region {region}")
                return None

        except Exception as e:
            self.logger.error(f"Error capturing region {region}: {e}")
            return None

    def get_pixel_color(self, x: int, y: int, sample_size: int = 3) -> Optional[Tuple[int, int, int]]:
        """
        Retrieves the color of a pixel at the given coordinates,
        using an optimized sampling method with caching.
        """
        try:
            effective_sample_size = max(sample_size, 5)
            half_size = effective_sample_size // 2
            region = (x - half_size, y - half_size, effective_sample_size, effective_sample_size)

            frame = self.capture_region(region, use_cache=True)
            if frame is None:
                return None

            center_x = effective_sample_size // 2
            center_y = effective_sample_size // 2

            if sample_size == 1:
                if frame.shape[0] > center_y and frame.shape[1] > center_x:
                    pixel = frame[center_y, center_x]
                    return (int(pixel[0]), int(pixel[1]), int(pixel[2]))
            else:
                start_x = center_x - sample_size // 2
                end_x = start_x + sample_size
                start_y = center_y - sample_size // 2
                end_y = start_y + sample_size

                start_x = max(0, start_x)
                start_y = max(0, start_y)
                end_x = min(frame.shape[1], end_x)
                end_y = min(frame.shape[0], end_y)

                sample_region = frame[start_y:end_y, start_x:end_x]
                avg_color = np.mean(sample_region.reshape(-1, 3), axis=0)
                return (int(avg_color[0]), int(avg_color[1]), int(avg_color[2]))

            return None

        except Exception as e:
            self.logger.error(f"Error getting pixel color at ({x}, {y}): {e}")
            return None

    def is_color_similar(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int], tolerance: int = 20) -> bool:
        """Compares two colors with a given tolerance."""
        try:
            diff = np.abs(np.array(color1) - np.array(color2))
            return bool(np.all(diff <= tolerance))
        except Exception as e:
            self.logger.error(f"Error comparing colors: {e}")
            return False

    def find_color_vectorized(self, frame: np.ndarray, target_color: Tuple[int, int, int],
                                tolerance: int = 20) -> Optional[Tuple[int, int]]:
        """Searches for a target color within a frame using vectorized operations."""
        try:
            target = np.array(target_color)
            diff = np.abs(frame - target)
            mask = np.all(diff <= tolerance, axis=2)

            coords = np.where(mask)
            if len(coords[0]) > 0:
                return (int(coords[1][0]), int(coords[0][0]))

            return None

        except Exception as e:
            self.logger.error(f"Error in vectorized color search: {e}")
            return None

    def find_color_in_region(self, target_color: Tuple[int, int, int],
                               region: Tuple[int, int, int, int],
                               tolerance: int = 20) -> Optional[Tuple[int, int]]:
        """Searches for a color within a specified screen region, leveraging caching."""
        try:
            x, y, width, height = region
            frame = self.capture_region(region, use_cache=True)

            if frame is None:
                return None

            relative_coords = self.find_color_vectorized(frame, target_color, tolerance)

            if relative_coords:
                rel_x, rel_y = relative_coords
                return (x + rel_x, y + rel_y)

            return None

        except Exception as e:
            self.logger.error(f"Error finding color in region: {e}")
            return None

    def calculate_accept_button_position(self, window_info: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """Calculates the expected position of the 'Accept' button relative to the window."""
        try:
            pos_x, pos_y, width, height = window_info
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
        Verifies the color of the 'Accept' button within the game window.
        """
        try:
            button_x, button_y = self.calculate_accept_button_position(window_info)

            sample_region = (button_x - 5, button_y - 5, 11, 11)
            frame = self.capture_region(sample_region, use_cache=True)

            if frame is None:
                return False

            center_pixels = frame[4:7, 4:7]
            avg_color = np.mean(center_pixels.reshape(-1, 3), axis=0)

            avg_color_int = (int(avg_color[0]), int(avg_color[1]), int(avg_color[2]))
            is_similar = self.is_color_similar(avg_color_int, target_color, tolerance)

            if self.capture_count % 10 == 0:
                if is_similar:
                    self.logger.debug(f"Accept button color verified at ({button_x}, {button_y}): {avg_color_int}")
                else:
                    self.logger.debug(f"Accept button color mismatch at ({button_x}, {button_y}): {avg_color_int} vs {target_color}")

            return is_similar

        except Exception as e:
            self.logger.error(f"Error verifying Accept button color: {e}")
            return False

    def get_status(self) -> dict:
        """Gets current service status, including cache and window information."""
        cs2_window_info = self.get_window_info()
        cache_hit_ratio = (self.cache_hits / max(1, self.capture_count)) * 100

        return {
            "dxcam_enabled": True,
            "camera_initialized": self.camera is not None,
            "cache_entries": len(self.frame_cache),
            "capture_count": self.capture_count,
            "cache_hits": self.cache_hits,
            "cache_hit_ratio": f"{cache_hit_ratio:.1f}%",
            "cs2_window_found": cs2_window_info is not None,
            "cs2_window_info": cs2_window_info,
            "cs2_window_foreground": self.is_window_foreground(),
            "service_ready": True
        }

    def __del__(self):
        """Cleans up DXcam resources when the object is destroyed."""
        if hasattr(self, 'camera') and self.camera:
            try:
                self.camera.release()
                self.logger.info(f"DXcam released. Stats - Captures: {getattr(self, 'capture_count', 0)}, Cache hits: {getattr(self, 'cache_hits', 0)}")
            except Exception:
                pass