"""
Data repositories for configuration and CSV pattern management.
"""
import os
import json
import logging
import time
import shutil
from typing import Dict, List, Any, Optional
from pathlib import Path

from core.models.recoil_data import RecoilData


class ConfigRepository:
    """Repository for JSON configuration file management."""

    def __init__(self, config_file: str = "config.json"):
        self.logger = logging.getLogger("ConfigRepository")
        self.config_file = config_file
        self.logger.info(
            "Config repository initialized (file: %s)", config_file)

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            if not os.path.exists(self.config_file):
                self.logger.warning(
                    "Configuration file not found: %s",
                    self.config_file)
                return {}

            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.logger.debug("Configuration loaded successfully")
            return config

        except json.JSONDecodeError as e:
            self.logger.error("JSON decode error: %s", e)
            return {}
        except Exception as e:
            self.logger.error("Configuration loading failed: %s", e)
            return {}

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to JSON file."""
        try:
            # Save configuration directly (no backup creation)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            self.logger.debug("Configuration saved successfully")
            return True

        except Exception as e:
            self.logger.error("Configuration save failed: %s", e)
            return False


class CSVRepository:
    """Repository for CSV pattern file management."""

    SENSITIVITY_MULTIPLIER = 2.45  # Conversion factor for sensitivity

    def __init__(self, patterns_folder: str = "patterns"):
        self.logger = logging.getLogger("CSVRepository")
        self.patterns_folder = Path(patterns_folder)

        # Ensure patterns directory exists
        self.patterns_folder.mkdir(exist_ok=True)

        self.logger.info(
            "CSV repository initialized (folder: %s)", patterns_folder)

    def load_weapon_pattern(
            self,
            filename: str,
            game_sensitivity: float = 1.0) -> List[RecoilData]:
        """Load recoil pattern from CSV file with sensitivity applied."""
        try:
            file_path = self.patterns_folder / filename

            if not file_path.exists():
                self.logger.warning("Pattern file not found: %s", file_path)
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
                        # Apply sensitivity conversion
                        dx = float(
                            parts[0]) * self.SENSITIVITY_MULTIPLIER / game_sensitivity
                        dy = float(
                            parts[1]) * self.SENSITIVITY_MULTIPLIER / game_sensitivity
                        delay = round(float(parts[2]), 1)

                        pattern.append(RecoilData(dx=dx, dy=dy, delay=delay))
                    else:
                        self.logger.warning(
                            "Invalid line %s in %s: %s", line_num, filename, line)

                except ValueError as e:
                    self.logger.warning(
                        "Parse error line %s in %s: %s", line_num, filename, e)
                    continue

            self.logger.info(
                "Pattern loaded from %s: %s points", filename, len(pattern))

            # Debug logging for first few points
            if pattern and self.logger.isEnabledFor(logging.DEBUG):
                for i in range(min(3, len(pattern))):
                    p = pattern[i]
                    self.logger.debug(
                        "  Point %s: dx=%.2f, dy=%.2f, delay=%s",
                        i, p.dx, p.dy, p.delay)

            return pattern

        except Exception as e:
            self.logger.error("Pattern loading failed for %s: %s", filename, e)
            return []

    def pattern_exists(self, filename: str) -> bool:
        """Check if pattern file exists."""
        file_path = self.patterns_folder / filename
        return file_path.exists() and file_path.is_file()
