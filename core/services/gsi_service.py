"""
Game State Integration service for Counter-Strike 2.
"""
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler

from core.models.player_state import PlayerState


class GSIRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for GSI data reception."""

    def __init__(self, gsi_service, *args, **kwargs):
        self.gsi_service = gsi_service
        super().__init__(*args, **kwargs)

    def do_POST(self):
        """Handle POST requests from CS2 GSI."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_response(400)
                self.end_headers()
                return

            raw_data = self.rfile.read(content_length)

            try:
                gsi_data = json.loads(raw_data.decode('utf-8'))
            except json.JSONDecodeError as e:
                self.gsi_service.logger.error("JSON decode error: %s", e)
                self.send_response(400)
                self.end_headers()
                return

            self.gsi_service._process_gsi_data(gsi_data)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')

        except Exception as e:
            self.gsi_service.logger.error("Request handling error: %s", e)
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        """Disable default HTTP logging."""
        pass


class GSIService:
    """Game State Integration service for CS2."""

    def __init__(self, host: str = "127.0.0.1", port: int = 59873):
        self.logger = logging.getLogger("GSIService")
        self.host = host
        self.port = port

        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False

        self.last_update_time = 0.0
        self.update_callbacks: Dict[str, Callable[[PlayerState], None]] = {}
        self.current_player_state: Optional[PlayerState] = None
        self.connection_status = "Disconnected"

        self.logger.info("GSI Service initialized on %s:%s", host, port)

    def start_server(self) -> bool:
        """Start the GSI HTTP server."""
        if self.is_running:
            return True

        try:
            def handler_factory(*args, **kwargs):
                return GSIRequestHandler(self, *args, **kwargs)

            self.server = HTTPServer((self.host, self.port), handler_factory)

            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True,
                name="GSIServer"
            )
            self.server_thread.start()

            self.is_running = True
            self.connection_status = "Listening"

            self.logger.info("GSI server started on %s:%s", self.host, self.port)
            return True

        except Exception as e:
            self.logger.error("Failed to start GSI server: %s", e)
            self.connection_status = "Error"
            return False

    def stop_server(self) -> bool:
        """Stop the GSI HTTP server."""
        if not self.is_running:
            return True

        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()

            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=2.0)

            self.is_running = False
            self.connection_status = "Stopped"

            self.logger.info("GSI server stopped")
            return True

        except Exception as e:
            self.logger.error("Error stopping GSI server: %s", e)
            return False

    def _run_server(self):
        """Server run loop."""
        try:
            if self.server is None:
                self.logger.warning("Server is None, cannot start serve_forever")
                return
            self.server.serve_forever()
        except Exception as e:
            if self.is_running:
                self.logger.error("Server error: %s", e)
        finally:
            self.is_running = False
            self.connection_status = "Disconnected"

    def _process_gsi_data(self, gsi_data: Dict[str, Any]) -> None:
        """Process incoming GSI data."""
        try:
            self.connection_status = "Connected"
            self.last_update_time = time.time()

            player_state = self._extract_player_state(gsi_data)

            if player_state:
                self.current_player_state = player_state

                for callback_name, callback in self.update_callbacks.items():
                    try:
                        callback(player_state)
                    except Exception as e:
                        self.logger.error(
                            "Callback '%s' error: %s", callback_name, e)

        except Exception as e:
            self.logger.error("GSI data processing error: %s", e)

    def _extract_player_state(
            self, gsi_data: Dict[str, Any]) -> Optional[PlayerState]:
        """Extract player state from GSI data."""
        try:
            player_data = gsi_data.get("player", {})
            if not player_data:
                return None

            activity = player_data.get("activity", "unknown")
            state = player_data.get("state", {})
            weapons_data = player_data.get("weapons", {})

            weapons = self._extract_weapons(weapons_data)

            active_weapon = None
            for weapon in weapons.values():
                if weapon.state == "active":
                    active_weapon = weapon
                    break

            return PlayerState(
                activity=activity,
                health=state.get("health", 0),
                armor=state.get("armor", 0),
                flashing=state.get("flashing", 0),
                burning=state.get("burning", 0),
                weapons=weapons,
                active_weapon=active_weapon,
                timestamp=time.time()
            )

        except Exception as e:
            self.logger.error("Player state extraction error: %s", e)
            return None

    def _extract_weapons(self, weapons_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract weapons from GSI data."""
        from core.models.player_state import WeaponState

        weapons = {}

        for slot, weapon_data in weapons_data.items():
            try:
                weapon = WeaponState(
                    name=weapon_data.get("name", "unknown"),
                    paintkit=weapon_data.get("paintkit", "default"),
                    type=weapon_data.get("type", "unknown"),
                    state=weapon_data.get("state", "inactive"),
                    ammo_clip=weapon_data.get("ammo_clip", 0),
                    ammo_clip_max=weapon_data.get("ammo_clip_max", 0),
                    ammo_reserve=weapon_data.get("ammo_reserve", 0)
                )
                weapons[slot] = weapon

            except Exception as e:
                self.logger.warning(
                    "Weapon extraction error for slot %s: %s", slot, e)
                continue

        return weapons

    def register_callback(
            self, name: str, callback: Callable[[PlayerState], None]) -> None:
        """Register callback for GSI updates."""
        self.update_callbacks[name] = callback
        self.logger.debug("Callback registered: %s", name)

    def unregister_callback(self, name: str) -> None:
        """Unregister GSI update callback."""
        if name in self.update_callbacks:
            del self.update_callbacks[name]
            self.logger.debug("Callback unregistered: %s", name)

    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information."""
        return {
            "status": self.connection_status,
            "is_running": self.is_running,
            "endpoint": f"http://{self.host}:{self.port}",
            "last_update": self.last_update_time,
            "time_since_update": (time.time() - self.last_update_time
                                  if self.last_update_time > 0 else None),
            "registered_callbacks": len(self.update_callbacks),
            "current_state_available": self.current_player_state is not None
        }
