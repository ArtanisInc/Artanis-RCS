"""
Text-to-speech service using Windows SAPI with simplified architecture.
"""
import logging
from typing import Optional

try:
    import win32com.client
    import pythoncom
    SAPI_AVAILABLE = True
except ImportError:
    SAPI_AVAILABLE = False
    win32com = None
    pythoncom = None


class TTSService:
    """Simplified text-to-speech service with direct SAPI calls and purge before speak."""

    def __init__(self, enabled: bool = True):
        self.logger = logging.getLogger("TTSService")
        self.enabled = enabled and SAPI_AVAILABLE

        # Voice configuration
        self.voice_rate = 4
        self.voice_volume = 65

        # SAPI instance
        self.voice = None

        if self.enabled:
            self._initialize_sapi()

        self.logger.debug("TTS service initialized (enabled: %s)", self.enabled)

    def _initialize_sapi(self) -> bool:
        """Initialize SAPI instance."""
        if not SAPI_AVAILABLE or not pythoncom or not win32com:
            return False

        try:
            # Initialize COM
            pythoncom.CoInitialize()

            # Create SAPI voice object
            self.voice = win32com.client.Dispatch("SAPI.SpVoice")
            self.voice.Rate = self.voice_rate
            self.voice.Volume = self.voice_volume

            # Select preferred voice
            self._select_preferred_voice()

            # Test with silent speech
            self.voice.Speak("", 3)  # Test with purge + async flag
            self.logger.debug("SAPI initialized successfully")
            return True

        except Exception as e:
            self.logger.error("SAPI initialization failed: %s", e)
            self.enabled = False
            return False

    def _select_preferred_voice(self) -> None:
        """Select English voice if available, otherwise use default."""
        if not self.voice:
            return

        try:
            voices = self.voice.GetVoices()

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
                    self.voice.Voice = voice_item
                    self.logger.debug(
                        "Selected English voice: %s",
                        voice_item.GetDescription())
                    return

            # Use default voice if no English voice found
            default_voice = self.voice.Voice.GetDescription()
            self.logger.debug("Using default voice: %s", default_voice)

        except Exception as e:
            self.logger.warning("Voice selection failed: %s", e)

    @staticmethod
    def normalize_weapon_pronunciation(text: str) -> str:
        """Normalize weapon names for better pronunciation."""
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

    def speak(self, message: str) -> bool:
        """Speak message with purge before speak enabled."""
        if not self.enabled or not self.voice or not message.strip():
            return False

        try:
            message = self.normalize_weapon_pronunciation(message.strip())

            # Use flag 3 (purge + async) - stops current speech, speaks new message without blocking
            self.voice.Speak(message, 3)

            self.logger.debug("TTS spoke with purge: '%s'", message)
            return True

        except Exception as e:
            self.logger.error("Failed to speak message: %s", e)
            return False

    def speak_interrupt_previous(self, message: str) -> bool:
        """Interrupt current speech and speak new message (same as speak with purge)."""
        return self.speak(message)

    def speak_immediate(self, message: str) -> bool:
        """Speak message immediately with purge before speak."""
        return self.speak(message)

    def clear_queue(self) -> None:
        """Clear any pending speech (stop current speech)."""
        if not self.enabled or not self.voice:
            return

        try:
            self.voice.Speak("", 3)  # Purge any current speech (async)
            self.logger.debug("Speech cleared")
        except Exception as e:
            self.logger.error("Failed to clear speech: %s", e)

    def set_voice_properties(
            self,
            rate: Optional[int] = None,
            volume: Optional[int] = None) -> bool:
        """Configure voice properties."""
        if not self.enabled or not self.voice:
            return False

        try:
            if rate is not None:
                self.voice_rate = max(-10, min(10, rate))
                self.voice.Rate = self.voice_rate

            if volume is not None:
                self.voice_volume = max(0, min(100, volume))
                self.voice.Volume = self.voice_volume

            # Get voice name for logging
            voice_name = "Unknown"
            try:
                voice_desc = self.voice.Voice.GetDescription()
                # Extract short name (e.g., "Microsoft Zira Desktop" -> "Zira")
                voice_parts = voice_desc.split()
                voice_name = voice_parts[1] if len(voice_parts) > 1 else voice_desc
            except Exception:
                voice_name = "Default"

            self.logger.info(
                "TTS initialized: %s voice, Rate: %s, Volume: %s",
                voice_name, self.voice_rate, self.voice_volume)
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
                if not self.voice:
                    if not self._initialize_sapi():
                        self.enabled = False
                        return False
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
        try:
            # Stop any ongoing speech
            if self.voice:
                try:
                    self.voice.Speak("", 3)  # Purge any current speech (async)
                except Exception as stop_error:
                    self.logger.warning("Error stopping SAPI: %s", stop_error)
                finally:
                    self.voice = None

            # Clean up COM
            if SAPI_AVAILABLE and pythoncom:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass  # COM might not be initialized

            self.logger.info("TTS service stopped")

        except Exception as e:
            self.logger.error("Error stopping TTS service: %s", e)

    def is_enabled(self) -> bool:
        """Check if TTS service is enabled."""
        return self.enabled
