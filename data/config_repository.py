"""
Data repositories for configuration and CSV pattern management.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from core.models.recoil_data import RecoilData


# JSON Schema for configuration validation
CONFIG_SCHEMA = {
    "type": "object",
    "required": ["game_sensitivity", "weapons"],
    "properties": {
        "game_sensitivity": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 10.0
        },
        "features": {
            "type": "object",
            "properties": {
                "tts_enabled": {"type": "boolean"},
                "bomb_timer_enabled": {"type": "boolean"},
                "auto_accept_enabled": {"type": "boolean"},
                "follow_rcs_enabled": {"type": "boolean"}
            }
        },
        "gsi": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "server_host": {"type": "string"},
                "server_port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                "low_ammo_threshold": {"type": "integer", "minimum": 0}
            }
        },
        "weapons": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "length", "multiple", "sleep_divider"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "display_name": {"type": "string"},
                    "length": {"type": "integer", "minimum": 1},
                    "multiple": {"type": "integer", "minimum": 1},
                    "sleep_divider": {"type": "number", "minimum": 0.1},
                    "sleep_suber": {"type": "number"},
                    "jitter_timing": {"type": "number", "minimum": 0},
                    "jitter_movement": {"type": "number", "minimum": 0}
                }
            }
        },
        "hotkeys": {
            "type": "object"
        }
    }
}


class ConfigRepository:
    """Repository for JSON configuration file management."""

    def __init__(self, config_file: str = "config.json"):
        self.logger = logging.getLogger("ConfigRepository")
        self.config_file = config_file
        self.logger.info(f"Config repository initialized (file: {config_file})")

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file with schema validation."""
        try:
            if not os.path.exists(self.config_file):
                self.logger.warning(f"Configuration file not found: {self.config_file}")
                return {}

            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Validate against schema
            validation_errors = self._validate_config_schema(config)
            if validation_errors:
                self.logger.warning(f"Configuration validation warnings: {', '.join(validation_errors)}")
                # Continue loading despite warnings - let ConfigService handle defaults

            self.logger.debug("Configuration loaded successfully")
            return config

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in {self.config_file}: {e}")
            return {}
        except (IOError, OSError) as e:
            self.logger.error(f"Failed to read configuration file {self.config_file}: {e}")
            return {}
        except Exception as e:
            self.logger.critical(f"Unexpected error loading configuration: {e}", exc_info=True)
            return {}

    def _validate_config_schema(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema. Returns list of validation errors."""
        errors = []

        # Check required top-level fields
        if "game_sensitivity" not in config:
            errors.append("Missing 'game_sensitivity'")
        elif not isinstance(config["game_sensitivity"], (int, float)):
            errors.append("'game_sensitivity' must be a number")
        elif not (0.1 <= config["game_sensitivity"] <= 10.0):
            errors.append("'game_sensitivity' must be between 0.1 and 10.0")

        if "weapons" not in config:
            errors.append("Missing 'weapons' array")
        elif not isinstance(config["weapons"], list):
            errors.append("'weapons' must be an array")
        elif len(config["weapons"]) == 0:
            errors.append("'weapons' array cannot be empty")
        else:
            # Validate each weapon
            for idx, weapon in enumerate(config["weapons"]):
                if not isinstance(weapon, dict):
                    errors.append(f"Weapon at index {idx} must be an object")
                    continue

                # Check required weapon fields
                for field in ["name", "length", "multiple", "sleep_divider"]:
                    if field not in weapon:
                        errors.append(f"Weapon '{weapon.get('name', idx)}' missing required field '{field}'")

                # Validate weapon field types and ranges
                if "length" in weapon and (not isinstance(weapon["length"], int) or weapon["length"] < 1):
                    errors.append(f"Weapon '{weapon.get('name')}' has invalid 'length'")
                if "multiple" in weapon and (not isinstance(weapon["multiple"], int) or weapon["multiple"] < 1):
                    errors.append(f"Weapon '{weapon.get('name')}' has invalid 'multiple'")
                if "sleep_divider" in weapon and (not isinstance(weapon["sleep_divider"], (int, float)) or weapon["sleep_divider"] <= 0):
                    errors.append(f"Weapon '{weapon.get('name')}' has invalid 'sleep_divider'")

        return errors

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to JSON file."""
        try:
            # Save configuration directly (no backup creation)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            self.logger.debug("Configuration saved successfully")
            return True

        except (IOError, OSError) as e:
            self.logger.error(f"Failed to write configuration file {self.config_file}: {e}")
            return False
        except (TypeError, ValueError) as e:
            self.logger.error(f"Invalid configuration data for JSON serialization: {e}")
            return False
        except Exception as e:
            self.logger.critical(f"Unexpected error saving configuration: {e}", exc_info=True)
            return False


class CSVRepository:
    """Repository for CSV pattern file management."""

    SENSITIVITY_MULTIPLIER = 2.45  # Conversion factor for sensitivity

    def __init__(self, patterns_folder: str = "patterns"):
        self.logger = logging.getLogger("CSVRepository")
        self.patterns_folder = Path(patterns_folder)

        self.patterns_folder.mkdir(exist_ok=True)

        self.logger.info(f"CSV repository initialized (folder: {patterns_folder})")

    def load_weapon_pattern(
            self,
            filename: str,
            game_sensitivity: float = 1.0) -> List[RecoilData]:
        """Load recoil pattern from CSV file with sensitivity applied."""
        try:
            file_path = self.patterns_folder / filename

            if not file_path.exists():
                self.logger.warning(f"Pattern file not found: {file_path}")
                return []

            pattern = []

            # Read file with UTF-8-sig to handle BOM
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        dx = float(
                            parts[0]) * self.SENSITIVITY_MULTIPLIER / game_sensitivity
                        dy = float(
                            parts[1]) * self.SENSITIVITY_MULTIPLIER / game_sensitivity
                        delay = round(float(parts[2]), 1)

                        pattern.append(RecoilData(dx=dx, dy=dy, delay=delay))
                    else:
                        self.logger.warning(
                            f"Invalid line {line_num} in {filename}: {line}")

                except ValueError as e:
                    self.logger.warning(
                        f"Parse error line {line_num} in {filename}: {e}")
                    continue

            self.logger.debug(f"Pattern loaded from {filename}: {len(pattern)} points")

            # Debug logging for first few points
            if pattern and self.logger.isEnabledFor(logging.DEBUG):
                for i in range(min(3, len(pattern))):
                    p = pattern[i]
                    self.logger.debug(
                        f"  Point {i}: dx={p.dx:.2f}, dy={p.dy:.2f}, delay={p.delay}")

            return pattern

        except Exception as e:
            self.logger.error(f"Pattern loading failed for {filename}: {e}")
            return []

    def pattern_exists(self, filename: str) -> bool:
        """Check if pattern file exists."""
        file_path = self.patterns_folder / filename
        return file_path.exists() and file_path.is_file()
