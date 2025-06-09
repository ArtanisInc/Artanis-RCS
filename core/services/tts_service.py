"""
Text-to-speech service using Windows SAPI with thread-safe architecture.
"""
import logging
import threading
import queue
import time
from typing import Optional, Dict, Any
from enum import Enum

try:
    import win32com.client
    import pythoncom
    SAPI_AVAILABLE = True
except ImportError:
    SAPI_AVAILABLE = False


class TTSPriority(Enum):
    """TTS announcement priorities for queue management."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class SAPIManager:
    """Manages SAPI voice instances and COM initialization."""

    def __init__(self, voice_rate: int = 4, voice_volume: int = 65):
        self.voice_rate = voice_rate
        self.voice_volume = voice_volume
        self.logger = logging.getLogger("SAPIManager")

    def create_voice_instance(self) -> Optional[Any]:
        """Create and configure SAPI voice instance."""
        try:
            # Initialize COM for current thread
            pythoncom.CoInitialize()

            # Create SAPI voice object
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            voice.Rate = self.voice_rate
            voice.Volume = self.voice_volume

            # Select French voice if available
            self._select_preferred_voice(voice)

            return voice

        except Exception as e:
            self.logger.error("Failed to create SAPI voice instance: %s", e)
            return None

    def _select_preferred_voice(self, voice) -> None:
        """Select English voice if available, otherwise use default."""
        try:
            voices = voice.GetVoices()

            for i in range(voices.Count):
                voice_item = voices.Item(i)
                voice_name = voice_item.GetDescription().lower()

                # Prioritize English voices
                if any(
                    keyword in voice_name for keyword in [
                        "english",
                        "en-us",
                        "us",
                        "uk"]):
                    voice.Voice = voice_item
                    self.logger.info(
                        "Selected English voice: %s",
                        voice_item.GetDescription())
                    return

            # Use default voice if no English voice found
            default_voice = voice.Voice.GetDescription()
            self.logger.info("Using default voice: %s", default_voice)

        except Exception as e:
            self.logger.warning("Voice selection failed: %s", e)

    @staticmethod
    def cleanup_com() -> None:
        """Clean up COM resources."""
        try:
            pythoncom.CoUninitialize()
        except BaseException:
            pass  # COM might not be initialized


class TTSWorker:
    """Worker thread for processing TTS announcements."""

    def __init__(
            self,
            tts_queue: queue.PriorityQueue,
            stop_event: threading.Event,
            voice_rate: int,
            voice_volume: int):
        self.tts_queue = tts_queue
        self.stop_event = stop_event
        self.voice_rate = voice_rate
        self.voice_volume = voice_volume
        self.logger = logging.getLogger("TTSWorker")

    def run(self) -> None:
        """Main worker loop with COM-safe SAPI handling."""
        self.logger.debug("TTS worker thread started")

        # Initialize SAPI for this thread
        sapi_manager = SAPIManager(self.voice_rate, self.voice_volume)
        worker_voice = sapi_manager.create_voice_instance()

        if not worker_voice:
            self.logger.error("Failed to initialize SAPI in worker thread")
            return

        try:
            while not self.stop_event.is_set():
                try:
                    # Get next announcement with timeout
                    priority, message = self.tts_queue.get(timeout=1.0)

                    self.logger.debug(
                        "Processing TTS (priority %s): %s", priority, message)

                    # Handle interruption for high priority messages
                    if priority == 1:  # Critical priority
                        worker_voice.Speak("", 2)  # Stop current speech
                        self.logger.debug(
                            "Speech interrupted for critical message")

                    # Speak the message
                    worker_voice.Speak(message, 0)  # Synchronous

                    # Mark task as done
                    self.tts_queue.task_done()

                except queue.Empty:
                    continue
                except Exception as e:
                    self.logger.error("TTS worker error: %s", e)

                    # Attempt to recreate SAPI instance on error
                    try:
                        worker_voice = sapi_manager.create_voice_instance()
                        if not worker_voice:
                            self.logger.error(
                                "Failed to recreate SAPI instance")
                            break
                    except Exception as recreation_error:
                        self.logger.error(
                            "SAPI recreation failed: %s", recreation_error)
                        break

        finally:
            # Clean up resources
            try:
                if worker_voice:
                    worker_voice.Speak("", 2)  # Stop any ongoing speech
            except BaseException:
                pass

            SAPIManager.cleanup_com()
            self.logger.debug("TTS worker thread terminated")


class TTSService:
    """Thread-safe text-to-speech service with queue management."""

    def __init__(self, enabled: bool = True):
        self.logger = logging.getLogger("TTSService")
        self.enabled = enabled and SAPI_AVAILABLE

        # Voice configuration
        self.voice_rate = 4
        self.voice_volume = 65

        # Threading components
        self.tts_queue = queue.PriorityQueue()
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        # Main thread SAPI instance (for immediate speech)
        self.main_voice = None

        if self.enabled:
            self._initialize_main_sapi()
            self._start_worker_thread()

        self.logger.info("TTS service initialized (enabled: %s)", self.enabled)

    def _initialize_main_sapi(self) -> bool:
        """Initialize SAPI instance for main thread."""
        try:
            sapi_manager = SAPIManager(self.voice_rate, self.voice_volume)
            self.main_voice = sapi_manager.create_voice_instance()

            if self.main_voice:
                # Test with silent speech
                self.main_voice.Speak("", 2)
                self.logger.debug("Main thread SAPI initialized successfully")
                return True
            else:
                self.logger.error("Failed to initialize main thread SAPI")
                return False

        except Exception as e:
            self.logger.error("Main SAPI initialization failed: %s", e)
            self.enabled = False
            return False

    def _start_worker_thread(self) -> None:
        """Start the worker thread for queue processing."""
        if not self.enabled or self.is_running:
            return

        try:
            self.stop_event.clear()
            worker = TTSWorker(
                self.tts_queue,
                self.stop_event,
                self.voice_rate,
                self.voice_volume)

            self.worker_thread = threading.Thread(
                target=worker.run,
                daemon=True,
                name="TTSWorker"
            )
            self.worker_thread.start()
            self.is_running = True

            self.logger.debug("TTS worker thread started")

        except Exception as e:
            self.logger.error("Failed to start TTS worker thread: %s", e)

    @staticmethod
    def normalize_weapon_pronunciation(text: str) -> str:
        weapon_pronunciations = {
            'ak47': 'AK forty-seven',
            'ak-47': 'AK forty-seven',
            'm4a4': 'M four A four',
            'm4a1': 'M four A one',
            'aug': 'AUG',
            'sg553': 'SG five fifty-three',
            'p90': 'P ninety',
            'mp5sd': 'MP five SD',
            'mp7': 'MP seven',
            'mp9': 'MP nine',
            'm249': 'M two forty-nine',
            'cz75': 'CZ seventy-five',
            'ump45': 'UMP forty-five',
            'mac10': 'MAC ten',
            'bizon': 'Bizon',
            'galil': 'Galil',
            'famas': 'FAMAS'
        }

        for key, value in weapon_pronunciations.items():
            text = text.replace(key, value).replace(key.upper(), value)
        return text

    def speak(
            self,
            message: str,
            priority: TTSPriority = TTSPriority.NORMAL) -> bool:
        """Add message to TTS queue."""
        if not self.enabled or not message.strip():
            return False

        try:
            message = TTSService.normalize_weapon_pronunciation(message)
            # Convert priority to queue value (lower number = higher priority)
            priority_value = 5 - priority.value
            self.tts_queue.put((priority_value, message.strip()))

            self.logger.debug("Message queued for TTS: '%s'", message)
            return True

        except Exception as e:
            self.logger.error("Failed to queue TTS message: %s", e)
            return False

    def speak_interrupt_previous(
            self,
            message: str,
            priority: TTSPriority = TTSPriority.HIGH) -> bool:
        """Interrupt current speech and speak new message immediately."""
        if not self.enabled or not message.strip():
            return False

        try:
            # Stop current speech in main thread
            if self.main_voice:
                try:
                    self.main_voice.Speak("", 2)  # Stop and purge
                except BaseException:
                    pass

            # Clear queue
            self.clear_queue()
            message = TTSService.normalize_weapon_pronunciation(message)

            # Add message with critical priority
            priority_value = 1  # Highest priority
            self.tts_queue.put((priority_value, message.strip()))

            self.logger.debug("Interrupting message added: '%s'", message)
            return True

        except Exception as e:
            self.logger.error("Failed to interrupt TTS: %s", e)
            return False

    def speak_immediate(self, message: str) -> bool:
        if not self.enabled or not self.main_voice or not message.strip():
            return False

        try:
            import threading
            if threading.current_thread() != threading.main_thread():
                self.logger.warning(
                    "speak_immediate called from worker thread, redirecting to queue")
                return self.speak(message, TTSPriority.HIGH)

            message = TTSService.normalize_weapon_pronunciation(message)
            self.logger.debug("Immediate TTS: %s", message)
            self.main_voice.Speak(message.strip(), 1)  # Asynchronous
            return True

        except Exception as e:
            self.logger.error("Immediate TTS failed: %s", e)
            return self.speak(message, TTSPriority.HIGH)  # Fallback to queue

    def clear_queue(self) -> None:
        """Clear all pending TTS messages."""
        if not self.enabled:
            return

        try:
            while not self.tts_queue.empty():
                try:
                    self.tts_queue.get_nowait()
                    self.tts_queue.task_done()
                except queue.Empty:
                    break

            self.logger.debug("TTS queue cleared")

        except Exception as e:
            self.logger.error("Failed to clear TTS queue: %s", e)

    def set_voice_properties(
            self,
            rate: Optional[int] = None,
            volume: Optional[int] = None) -> bool:
        """Configure voice properties."""
        if not self.enabled or not self.main_voice:
            return False

        try:
            if rate is not None:
                self.voice_rate = max(-10, min(10, rate))
                self.main_voice.Rate = self.voice_rate

            if volume is not None:
                self.voice_volume = max(0, min(100, volume))
                self.main_voice.Volume = self.voice_volume

            self.logger.info(
                "Voice properties updated (Rate: %s, Volume: %s)",
                self.voice_rate, self.voice_volume)
            return True

        except Exception as e:
            self.logger.error("Failed to set voice properties: %s", e)
            return False

    def set_enabled(self, enabled: bool) -> bool:
        """Enable or disable TTS service dynamically."""
        if not SAPI_AVAILABLE and enabled:
            self.logger.warning("SAPI not available, cannot enable TTS")
            return False

        if self.enabled == enabled:
            return True  # Already in desired state

        try:
            if enabled:
                # Enable TTS
                self.enabled = True
                if not self.main_voice:
                    if not self._initialize_main_sapi():
                        self.enabled = False
                        return False
                if not self.is_running:
                    self._start_worker_thread()
                self.logger.info("TTS service enabled")
            else:
                # Disable TTS
                self.stop()
                self.enabled = False
                self.logger.info("TTS service disabled")

            return True

        except Exception as e:
            self.logger.error("Failed to change TTS state: %s", e)
            return False

    def stop(self) -> None:
        """Stop TTS service and clean up resources."""
        if not self.is_running:
            return

        try:
            # Stop worker thread
            self.stop_event.set()

            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=2.0)

                if self.worker_thread.is_alive():
                    self.logger.warning(
                        "TTS worker thread did not terminate gracefully")

            # Clean up main thread SAPI
            if self.main_voice:
                try:
                    self.main_voice.Speak("", 2)  # Stop any ongoing speech
                except Exception as stop_error:
                    self.logger.warning(
                        "Error stopping main SAPI: %s", stop_error)
                finally:
                    self.main_voice = None

            # Clean up COM for main thread
            SAPIManager.cleanup_com()

            self.is_running = False
            self.logger.info("TTS service stopped")

        except Exception as e:
            self.logger.error("Error stopping TTS service: %s", e)

    def is_enabled(self) -> bool:
        """Check if TTS service is enabled."""
        return self.enabled
