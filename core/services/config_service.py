"""
Centralized configuration management service.
"""
import logging
from typing import Dict, List, Any, Optional

from core.models.weapon import WeaponProfile
from data.config_repository import ConfigRepository, CSVRepository


class ConfigurationValidator:
    """Validates configuration data integrity."""

    @staticmethod
    def validate_sensitivity(value: float) -> bool:
        """Validate sensitivity is within acceptable range."""
        return 0.1 <= value <= 10.0

    @staticmethod
    def validate_weapon_data(weapon_data: Dict[str, Any]) -> bool:
        """Validate weapon configuration data."""
        required_fields = ['name', 'length', 'multiple', 'sleep_divider']

        try:
            # Check required fields exist
            for field in required_fields:
                if field not in weapon_data:
                    return False

            # Validate data types and ranges
            name = weapon_data['name']
            if not isinstance(name, str) or not name.strip():
                return False

            length = weapon_data['length']
            if not isinstance(length, int) or length <= 0:
                return False

            multiple = weapon_data['multiple']
            if not isinstance(multiple, int) or multiple <= 0:
                return False

            sleep_divider = weapon_data['sleep_divider']
            if not isinstance(sleep_divider, (int, float)
                              ) or sleep_divider <= 0:
                return False

            return True

        except (KeyError, TypeError):
            return False

    @staticmethod
    def validate_features_data(features_data: Dict[str, Any]) -> bool:
        """Validate features configuration."""

        try:

            # Validate boolean features
            bool_features = ["tts_enabled", "bomb_timer_enabled"]
            for feature in bool_features:
                if feature in features_data:
                    if not isinstance(features_data[feature], bool):
                        return False

            return True

        except (KeyError, TypeError):
            return False


class WeaponManager:
    """Manages weapon profiles and operations."""

    def __init__(self, csv_repository: CSVRepository):
        self.csv_repository = csv_repository
        self.logger = logging.getLogger("WeaponManager")
        self.profiles: Dict[str, WeaponProfile] = {}

    def load_weapon_profiles(self,
                             weapons_config: List[Dict[str,
                                                       Any]],
                             game_sensitivity: float) -> Dict[str,
                                                              WeaponProfile]:
        """Load all weapon profiles from configuration."""
        profiles = {}

        for weapon_config in weapons_config:
            try:
                if not ConfigurationValidator.validate_weapon_data(
                        weapon_config):
                    self.logger.warning(
                        "Invalid weapon configuration: %s", weapon_config.get('name', 'unknown'))
                    continue

                name = weapon_config["name"]
                csv_file = f"{name}.csv"

                # Load recoil data with sensitivity applied
                recoil_data = self.csv_repository.load_weapon_pattern(
                    csv_file, game_sensitivity)
                if not recoil_data:
                    self.logger.warning(
                        "Pattern not found for weapon: %s", name)
                    continue

                # Create weapon profile
                profile = WeaponProfile(
                    name=name,
                    display_name=weapon_config.get("display_name", name),
                    recoil_pattern=recoil_data,
                    length=weapon_config.get("length", 30),
                    multiple=weapon_config.get("multiple", 6),
                    sleep_divider=weapon_config.get("sleep_divider", 6.0),
                    sleep_suber=weapon_config.get("sleep_suber", 0.0),
                    game_sensitivity=game_sensitivity
                )

                profiles[name] = profile
                self.logger.debug("Loaded weapon profile: %s", name)

            except Exception as e:
                self.logger.error(
                    "Failed to load weapon %s: %s",
                    weapon_config.get('name', 'unknown'), e)
                continue

        self.profiles = profiles
        if profiles:
            weapon_names = ", ".join(sorted(profiles.keys()))
            self.logger.info("Loaded %s weapon profiles: %s", len(profiles), weapon_names)
        else:
            self.logger.warning("No weapon profiles loaded")
        return profiles

    def update_weapon_sensitivity(
            self,
            weapon_name: str,
            new_sensitivity: float) -> bool:
        """Update sensitivity for specific weapon."""
        if weapon_name not in self.profiles:
            raise KeyError(f"Weapon not found: {weapon_name}")

        if not ConfigurationValidator.validate_sensitivity(new_sensitivity):
            raise ValueError(f"Invalid sensitivity value: {new_sensitivity}")

        return self.profiles[weapon_name].update_sensitivity(
            new_sensitivity, self.csv_repository)

    def update_all_weapons_sensitivity(self, new_sensitivity: float) -> int:
        """Update sensitivity for all weapons. Returns count of successful updates."""
        if not ConfigurationValidator.validate_sensitivity(new_sensitivity):
            raise ValueError(f"Invalid sensitivity value: {new_sensitivity}")

        success_count = 0
        for weapon_name in self.profiles.keys():
            try:
                if self.update_weapon_sensitivity(
                        weapon_name, new_sensitivity):
                    success_count += 1
            except Exception as e:
                self.logger.warning(
                    "Failed to update sensitivity for %s: %s", weapon_name, e)

        return success_count


class ConfigService:
    """Centralized configuration management service."""

    def __init__(
            self,
            config_repository: ConfigRepository,
            csv_repository: CSVRepository):
        self.logger = logging.getLogger("ConfigService")
        self.config_repository = config_repository
        self.csv_repository = csv_repository
        self.weapon_manager = WeaponManager(csv_repository)

        # Configuration data
        self.config = {}
        self.weapon_profiles: Dict[str, WeaponProfile] = {}
        self.hotkeys = {}

        # Load initial configuration
        self.load_config()

    def load_config(self) -> bool:
        """Load complete configuration from repository."""
        try:
            self.config = self.config_repository.load_config()
            if not self.config:
                self.logger.warning("Empty or missing configuration file")
                self._create_default_config()
                return False

            self._parse_and_validate_config()
            self.logger.info("Configuration loaded successfully")
            return True

        except Exception as e:
            self.logger.error("Configuration loading failed: %s", e)
            raise RuntimeError(f"Failed to load configuration: {e}")

    def save_config(self) -> bool:
        """Save current configuration to repository."""
        try:
            self._update_config_dict()
            success = self.config_repository.save_config(self.config)

            if success:
                self.logger.debug("Configuration saved successfully")
            else:
                self.logger.error("Configuration save failed")

            return success

        except Exception as e:
            self.logger.error("Configuration save error: %s", e)
            raise RuntimeError(f"Failed to save configuration: {e}")

    def _parse_and_validate_config(self) -> None:
        """Parse and validate loaded configuration."""
        # Get global sensitivity
        game_sensitivity = self.config.get("game_sensitivity", 1.0)
        if not ConfigurationValidator.validate_sensitivity(game_sensitivity):
            self.logger.warning(
                "Invalid global sensitivity %s, using default", game_sensitivity)
            game_sensitivity = 1.0
            self.config["game_sensitivity"] = game_sensitivity

        # Load weapon profiles
        weapons_config = self.config.get("weapons", [])
        self.weapon_profiles = self.weapon_manager.load_weapon_profiles(
            weapons_config, game_sensitivity)

        # Load hotkeys
        self.hotkeys = self.config.get("hotkeys", {})

        # Validate and normalize features
        self._validate_and_normalize_features()

    def _validate_and_normalize_features(self) -> None:
        """Validate and normalize features configuration."""
        features = self.config.get("features", {})

        if not ConfigurationValidator.validate_features_data(features):
            self.logger.warning(
                "Invalid features configuration, applying defaults")
            features = {}

        # Apply defaults for missing values
        defaults = {
            "tts_enabled": True,
            "bomb_timer_enabled": True
        }

        for key, default_value in defaults.items():
            if key not in features:
                features[key] = default_value

        self.config["features"] = features

    def _create_default_config(self) -> None:
        """Create default configuration structure."""
        self.config = {
            "game_sensitivity": 1.0,
            "features": {
                "tts_enabled": True,
                "bomb_timer_enabled": True
            },
            "hotkeys": {},
            "weapons": []
        }
        self.logger.info("Created default configuration")

    def _update_config_dict(self) -> None:
        """Update configuration dictionary with current values."""
        # Update weapon profiles
        weapons_config = []
        for profile in self.weapon_profiles.values():
            weapons_config.append(profile.to_dict())

        self.config["weapons"] = weapons_config
        self.config["hotkeys"] = self.hotkeys

    def get_weapon_profile(self, name: str) -> Optional[WeaponProfile]:
        """Get weapon profile by name."""
        return self.weapon_profiles.get(name)

    def save_weapon_profile(self, profile: WeaponProfile) -> bool:
        """Save weapon profile and update configuration."""
        try:
            self.weapon_profiles[profile.name] = profile
            return self.save_config()
        except Exception as e:
            self.logger.error(
                "Failed to save weapon profile %s: %s",
                profile.name, e)
            return False

    def get_weapon_display_name(self, internal_name: str) -> Optional[str]:
        """Get weapon display name from internal name."""
        if not internal_name:
            return "Unknown weapon"

        # Try weapon profiles first
        profile = self.weapon_profiles.get(internal_name)
        if profile:
            return profile.display_name

        # Fallback to config lookup
        for weapon_data in self.config.get("weapons", []):
            if weapon_data.get("name") == internal_name:
                return weapon_data.get("display_name", internal_name)

        self.logger.warning(
            "Display name not found for weapon: %s", internal_name)
        return internal_name

    def update_weapon_sensitivity(
            self,
            weapon_name: str,
            new_sensitivity: float) -> bool:
        """Update sensitivity for specific weapon."""
        try:
            success = self.weapon_manager.update_weapon_sensitivity(
                weapon_name, new_sensitivity)
            if success:
                self.config["game_sensitivity"] = new_sensitivity
            return success
        except (KeyError, ValueError) as e:
            self.logger.error("Weapon sensitivity update failed: %s", e)
            return False

    def update_global_sensitivity(self, new_sensitivity: float) -> bool:
        """Update sensitivity for all weapons."""
        try:
            success_count = self.weapon_manager.update_all_weapons_sensitivity(
                new_sensitivity)
            total_weapons = len(self.weapon_profiles)

            if success_count > 0:
                self.config["game_sensitivity"] = new_sensitivity
                self.logger.info(
                    "Global sensitivity updated: %s (%s/%s weapons)", new_sensitivity, success_count, total_weapons)

            return success_count == total_weapons

        except ValueError as e:
            self.logger.error("Global sensitivity update failed: %s", e)
            return False

    def get_hotkey(self, key: str, default=None) -> Any:
        """Get hotkey value with optional default."""
        return self.hotkeys.get(key, default)

    def save_hotkeys(self, hotkeys: Dict[str, Any]) -> bool:
        """Save hotkeys configuration."""
        try:
            self.hotkeys.update(hotkeys)
            return self.save_config()
        except Exception as e:
            self.logger.error("Failed to save hotkeys: %s", e)
            return False

    def get_weapon_hotkeys(self) -> Dict[str, str]:
        """Get hotkeys assigned to weapons."""
        weapon_hotkeys = {}
        weapon_names = set(self.weapon_profiles.keys())

        for key, value in self.hotkeys.items():
            if key in weapon_names:
                weapon_hotkeys[key] = value

        return weapon_hotkeys

    def assign_weapon_hotkey(self, weapon_name: str, hotkey: str) -> bool:
        """Assign hotkey to weapon."""
        if weapon_name not in self.weapon_profiles:
            raise KeyError(f"Weapon not found: {weapon_name}")

        try:
            self.hotkeys[weapon_name] = hotkey
            return self.save_config()
        except Exception as e:
            self.logger.error("Failed to assign hotkey: %s", e)
            return False

    def remove_weapon_hotkey(self, weapon_name: str) -> bool:
        """Remove hotkey assignment for weapon."""
        try:
            if weapon_name in self.hotkeys:
                del self.hotkeys[weapon_name]
                return self.save_config()
            return True
        except Exception as e:
            self.logger.error("Failed to remove hotkey assignment: %s", e)
            return False
