"""
Game State Integration service for Counter-Strike 2.
"""
import json
import logging
import re
import threading
import time
import winreg
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor

from core.models.player_state import PlayerState


class GSIConfigService:
    """Service for managing GSI configuration file generation."""

    def __init__(self):
        self.logger = logging.getLogger("GSIConfigService")
        self.config_name = "rcs"
        self.config_filename = f"gamestate_integration_{self.config_name}.cfg"

    def generate_config_file(self, gsi_config: Dict[str, Any]) -> bool:
        """
        Generate GSI configuration file if it doesn't exist.
        """
        try:
            cs2_config_path = self._find_cs2_config_directory()

            if not cs2_config_path:
                self.logger.error("Could not locate CS2 configuration directory")
                return False

            config_file_path = cs2_config_path / self.config_filename

            if config_file_path.exists():
                self.logger.debug("GSI config file already exists: %s", config_file_path)
                return True

            config_content = self._generate_config_content(gsi_config)

            with open(config_file_path, 'w', encoding='utf-8') as f:
                f.write(config_content)

            self.logger.info("GSI config file created: %s", config_file_path)
            return True

        except Exception as e:
            self.logger.error("Failed to generate GSI config file: %s", e)
            return False

    def _find_cs2_config_directory(self) -> Optional[Path]:
        """Find CS2 configuration directory."""
        try:
            steam_paths = self._get_steam_paths()

            for steam_path in steam_paths:
                if not steam_path.exists():
                    continue

                cs2_config_path = steam_path / "steamapps/common/Counter-Strike Global Offensive/game/csgo/cfg"

                if cs2_config_path.exists():
                    self.logger.debug("Found CS2 config directory: %s", cs2_config_path)
                    return cs2_config_path

            return None

        except Exception as e:
            self.logger.error("Error finding CS2 config directory: %s", e)
            return None

    def _get_steam_paths(self) -> list[Path]:
        """Get Steam installation paths including custom library folders."""
        steam_paths = []
        main_steam_path = None

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
                install_path = winreg.QueryValueEx(key, "InstallPath")[0]
                main_steam_path = Path(install_path)
                steam_paths.append(main_steam_path)
        except (WindowsError, FileNotFoundError):
            pass

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"SOFTWARE\Valve\Steam") as key:
                install_path = winreg.QueryValueEx(key, "SteamPath")[0]
                main_steam_path = Path(install_path)
                steam_paths.append(main_steam_path)
        except (WindowsError, FileNotFoundError):
            pass

        if main_steam_path:
            library_paths = self._parse_libraryfolders_vdf(main_steam_path)
            for lib_path in library_paths:
                if lib_path not in steam_paths:
                    steam_paths.append(lib_path)

        self.logger.debug("Found Steam paths: %s", [str(p) for p in steam_paths])
        return steam_paths

    def _parse_libraryfolders_vdf(self, steam_path: Path) -> list[Path]:
        """Parse Steam's libraryfolders.vdf to find all library locations."""
        library_paths = []

        try:
            vdf_path = steam_path / "config" / "libraryfolders.vdf"

            if not vdf_path.exists():
                self.logger.debug("libraryfolders.vdf not found at %s", vdf_path)
                return library_paths

            with open(vdf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            path_pattern = r'"path"\s+"([^"]+)"'
            matches = re.findall(path_pattern, content, re.IGNORECASE)

            for match in matches:
                library_path = Path(match.replace('\\\\', '\\'))

                if library_path.exists():
                    library_paths.append(library_path)
                    self.logger.debug("Found Steam library: %s", library_path)
                else:
                    self.logger.debug("Steam library path does not exist: %s", library_path)

        except Exception as e:
            self.logger.warning("Error parsing libraryfolders.vdf: %s", e)

        return library_paths

    def _generate_config_content(self, gsi_config: Dict[str, Any]) -> str:
        """Generate the GSI configuration file content."""
        host = gsi_config.get("server_host", "127.0.0.1")
        port = gsi_config.get("server_port", 59873)
        uri = f"http://{host}:{port}"

        return f'''"Artanis RCS Integration"
{{
    "uri"                   "{uri}"
    "timeout"               "5.0"
    "buffer"                "0.1"
    "throttle"              "0.1"
    "heartbeat"             "10.0"
    "data"
    {{
        "player_state"          "1"
        "player_weapons"        "1"
        "round"                 "1"
        "bomb"                  "1"
    }}
}}'''


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

            self.gsi_service._submit_gsi_data(gsi_data)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')

        except Exception as e:
            self.gsi_service.logger.error("Request handling error: %s", e)
            self.send_response(500)
            self.end_headers()


class GSIService:
    """Game State Integration service for CS2."""

    def __init__(self, host: str = "127.0.0.1", port: int = 59873,
                 gsi_config: Optional[Dict[str, Any]] = None,
                 auto_generate_config: bool = True):
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
        self.lock = threading.Lock()

        self._payload_cache: Dict[str, Any] = {}
        self._last_payload_hash: Optional[str] = None
        self._processed_count = 0
        self._cache_hits = 0
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="GSI")

        self._tracked_fields = {
            'activity', 'health', 'armor', 'flashing', 'burning',
            'active_weapon_name', 'active_weapon_ammo', 'bomb_planted', 'has_defuse_kit'
        }
        self._last_field_values: Dict[str, Any] = {}

        self.config_service = GSIConfigService()

        config_status = "existing"
        if auto_generate_config and gsi_config:
            config_generated = self.config_service.generate_config_file(gsi_config)
            if config_generated:
                config_status = "auto-generated"
            else:
                self.logger.warning("GSI configuration file could not be generated automatically")
                config_status = "generation failed"

        self.logger.info("GSI Service ready: config %s, server on %s:%s", config_status, host, port)

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

            self.logger.debug("GSI server started on %s:%s", self.host, self.port)
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

            self._executor.shutdown(wait=True)

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

    def _submit_gsi_data(self, gsi_data: Dict[str, Any]) -> None:
        """Submit GSI data for async processing."""
        try:
            payload_str = json.dumps(gsi_data, sort_keys=True)
            payload_hash = hashlib.md5(payload_str.encode()).hexdigest()

            if payload_hash == self._last_payload_hash:
                self._cache_hits += 1
                return

            self._last_payload_hash = payload_hash

            self._executor.submit(self._process_gsi_data, gsi_data)

        except Exception as e:
            self.logger.error("GSI data submission error: %s", e)

    def _process_gsi_data(self, gsi_data: Dict[str, Any]) -> None:
        """Process incoming GSI data with change detection."""
        try:
            self.connection_status = "Connected"
            self.last_update_time = time.time()
            self._processed_count += 1

            player_state = self._extract_player_state(gsi_data)

            if player_state:
                current_fields = self._extract_tracked_fields(player_state)

                if self._has_significant_changes(current_fields):
                    self.current_player_state = player_state
                    self._last_field_values = current_fields

                    self._execute_callbacks_async(player_state)
                else:
                    if self.current_player_state:
                        self.current_player_state.timestamp = player_state.timestamp

        except Exception as e:
            self.logger.error("GSI data processing error: %s", e)

    def _extract_tracked_fields(self, player_state: PlayerState) -> Dict[str, Any]:
        """Extract fields we want to track for changes."""
        return {
            'activity': player_state.activity,
            'health': player_state.health,
            'armor': player_state.armor,
            'flashing': player_state.flashing,
            'burning': player_state.burning,
            'active_weapon_name': player_state.active_weapon.name if player_state.active_weapon else None,
            'active_weapon_ammo': player_state.active_weapon.ammo_clip if player_state.active_weapon else 0,
            'bomb_planted': player_state.bomb_planted,
            'has_defuse_kit': player_state.has_defuse_kit
        }

    def _has_significant_changes(self, current_fields: Dict[str, Any]) -> bool:
        """Check if there are significant changes worth processing."""
        if not self._last_field_values:
            return True

        for field, value in current_fields.items():
            if self._last_field_values.get(field) != value:
                return True

        return False

    def _execute_callbacks_async(self, player_state: PlayerState) -> None:
        """Execute callbacks asynchronously to avoid blocking."""
        for callback_name, callback in self.update_callbacks.items():
            try:
                self._executor.submit(self._safe_callback_execution, callback_name, callback, player_state)
            except Exception as e:
                self.logger.error("Callback submission error for '%s': %s", callback_name, e)

    def _safe_callback_execution(self, callback_name: str, callback: Callable, player_state: PlayerState) -> None:
        """Safely execute a callback with error handling."""
        try:
            callback(player_state)
        except Exception as e:
            self.logger.error("Callback '%s' execution error: %s", callback_name, e)

    def _extract_player_state(
            self, gsi_data: Dict[str, Any]) -> Optional[PlayerState]:
        """Extract player state from GSI data with caching."""
        try:
            player_data = gsi_data.get("player", {})
            if not player_data:
                return None

            activity = player_data.get("activity", "unknown")
            state = player_data.get("state", {})
            weapons_data = player_data.get("weapons", {})

            round_data = gsi_data.get("round", {})
            bomb_planted = round_data.get("bomb", "") == "planted"

            has_defuse_kit = "defusekit" in state

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
                timestamp=time.time(),
                has_defuse_kit=has_defuse_kit,
                bomb_planted=bomb_planted
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
        with self.lock:
            self.update_callbacks[name] = callback
            self.logger.debug("Callback registered: %s", name)

    def unregister_callback(self, name: str) -> None:
        """Unregister GSI update callback."""
        with self.lock:
            if name in self.update_callbacks:
                del self.update_callbacks[name]
                self.logger.debug("Callback unregistered: %s", name)

    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information"""

        return {
            "status": self.connection_status,
            "is_running": self.is_running,
        }