"""
Data models for CS2 player state from GSI.
"""
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class WeaponCategory(Enum):
    """Weapon categories for RCS eligibility."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MELEE = "melee"
    GRENADE = "grenade"
    C4 = "c4"
    UNKNOWN = "unknown"


@dataclass
class WeaponState:
    """Weapon state from GSI data."""

    name: str
    paintkit: str
    type: str
    state: str
    ammo_clip: int
    ammo_clip_max: int
    ammo_reserve: int

    def __post_init__(self):
        """Ensure ammo values are non-negative."""
        self.ammo_clip = max(0, self.ammo_clip)
        self.ammo_clip_max = max(0, self.ammo_clip_max)
        self.ammo_reserve = max(0, self.ammo_reserve)

    @property
    def is_active(self) -> bool:
        """Check if weapon is currently active."""
        return self.state == "active"

    @property
    def has_ammo_in_clip(self) -> bool:
        """Check if weapon has ammunition in clip."""
        return self.ammo_clip > 0

    @property
    def weapon_category(self) -> WeaponCategory:
        """Get weapon category for RCS logic."""
        weapon_name = self.name.lower()

        # Primary weapons eligible for RCS
        primary_weapons = [
            "ak47", "m4a1", "m4a4", "awp", "scar20", "g3sg1",
            "famas", "galil", "aug", "sg556", "ssg08",
            "p90", "mp5", "mp7", "mp9", "mac10", "ump45", "bizon",
            "nova", "mag7", "sawed", "xm1014", "m249", "negev"
        ]

        # CZ75 exception: pistol with RCS pattern
        if "cz75" in weapon_name:
            return WeaponCategory.PRIMARY

        if any(weapon in weapon_name for weapon in primary_weapons):
            return WeaponCategory.PRIMARY

        # Secondary weapons (pistols) - not eligible for RCS
        secondary_weapons = [
            "glock", "usp", "p2000", "p250", "fiveseven", "tec9",
            "deagle", "revolver", "dualies"
        ]
        if any(weapon in weapon_name for weapon in secondary_weapons):
            return WeaponCategory.SECONDARY

        # Melee weapons
        if "knife" in weapon_name or self.type == "knife":
            return WeaponCategory.MELEE

        # Grenades
        grenade_types = [
            "grenade", "flashbang", "smoke", "molotov", "incgrenade", "decoy"
        ]
        if any(grenade in weapon_name for grenade in grenade_types):
            return WeaponCategory.GRENADE

        # C4
        if "c4" in weapon_name:
            return WeaponCategory.C4

        return WeaponCategory.UNKNOWN

    @property
    def is_rcs_eligible(self) -> bool:
        """Check if weapon is eligible for RCS."""
        return (self.weapon_category == WeaponCategory.PRIMARY and
                self.is_active and
                self.has_ammo_in_clip)

    def get_pattern_name(self) -> Optional[str]:
        """Get pattern file name for this weapon."""
        weapon_pattern_map = {
            "weapon_ak47": "ak47",
            "weapon_m4a1": "m4a4",
            "weapon_m4a1_silencer": "m4a1",
            "weapon_m4a4": "m4a4",
            "weapon_famas": "famas",
            "weapon_galilar": "galil",
            "weapon_aug": "aug",
            "weapon_sg556": "sg553",
            "weapon_p90": "p90",
            "weapon_mp5sd": "mp5sd",
            "weapon_mp7": "mp7",
            "weapon_mp9": "mp9",
            "weapon_mac10": "mac10",
            "weapon_ump45": "ump45",
            "weapon_bizon": "bizon",
            "weapon_m249": "m249",
            "weapon_negev": "negev",
            "weapon_cz75a": "cz75"
        }

        return weapon_pattern_map.get(self.name)


@dataclass
class PlayerState:
    """Complete player state from GSI."""

    health: int
    armor: int
    flashing: int
    burning: int
    weapons: Dict[str, WeaponState]
    active_weapon: Optional[WeaponState]
    timestamp: float
    has_defuse_kit: bool = False
    bomb_planted: bool = False

    def __post_init__(self):
        """Clamp values to valid ranges."""
        self.health = max(0, min(100, self.health))
        self.armor = max(0, min(100, self.armor))
        self.flashing = max(0, min(255, self.flashing))
        self.burning = max(0, min(255, self.burning))

    @property
    def is_alive(self) -> bool:
        """Check if player is alive."""
        return self.health > 0

    @property
    def is_playing(self) -> bool:
        """Check if player is in active gameplay."""
        # CS2 GSI doesn't provide reliable activity state
        # Gameplay detection is handled via health check in is_combat_ready
        return True

    @property
    def is_combat_ready(self) -> bool:
        """Check if player is ready for combat."""
        return self.is_alive and self.is_playing

    @property
    def should_enable_rcs(self) -> bool:
        """Determine if RCS should be enabled."""
        if not self.is_combat_ready or not self.active_weapon:
            return False

        return self.active_weapon.is_rcs_eligible

    @property
    def rcs_weapon_pattern(self) -> Optional[str]:
        """Get RCS pattern name for current weapon."""
        if not self.should_enable_rcs or not self.active_weapon:
            return None

        return self.active_weapon.get_pattern_name()
