"""
Weapon profile model with recoil pattern subdivision algorithm.
"""
import logging
from typing import List, Dict, Any, Optional

import numpy as np

from core.models.recoil_data import RecoilData


class PatternSubdivisionAlgorithm:
    """Implements the precise pattern subdivision algorithm."""

    @staticmethod
    def subdivide(
            pattern: List[RecoilData],
            multiple: int,
            length: int) -> List[RecoilData]:
        """
        Subdivide recoil pattern with exact gap distribution.

        Reproduces the original mathematical algorithm:
        - Divide each point by subdivision factor
        - Track rounding errors with accumulation
        - Distribute gaps across last subdivision points

        Args:
            pattern: Original recoil pattern
            multiple: Subdivision factor
            length: Maximum pattern length to process

        Returns:
            Subdivided pattern with exact mathematical precision
        """
        if not pattern or multiple <= 1:
            return pattern[:length] if pattern else []

        # Process only up to specified length
        pattern_to_process = pattern[:length]
        result = []

        # Accumulation tracking (critical for precision)
        sum_x = 0.0
        sum_y = 0.0
        sum_x_original = 0.0
        sum_y_original = 0.0

        # Process each original point
        for i, point in enumerate(pattern_to_process):
            # Subdivide current point
            for j in range(multiple):
                # Floor division for each sub-point
                sub_dx = np.floor(point.dx / multiple)
                sub_dy = np.floor(point.dy / multiple)

                result.append(RecoilData(
                    dx=sub_dx,
                    dy=sub_dy,
                    delay=point.delay
                ))

                # Update subdivided sum
                sum_x += sub_dx
                sum_y += sub_dy

            # Update original sum
            sum_x_original += point.dx
            sum_y_original += point.dy

            # Calculate and distribute rounding gaps
            gap_x = int(round(sum_x_original - sum_x))
            gap_y = int(round(sum_y_original - sum_y))

            # Distribute X gap (last points of current subdivision)
            for k in range(gap_x):
                idx = (multiple * (i + 1)) - k - 1
                if 0 <= idx < len(result):
                    result[idx].dx += 1
                    sum_x += 1

            # Distribute Y gap (last points of current subdivision)
            for k in range(gap_y):
                idx = (multiple * (i + 1)) - k - 1
                if 0 <= idx < len(result):
                    result[idx].dy += 1
                    sum_y += 1

        return result


class WeaponProfile:
    """Weapon profile with optimized pattern calculation."""

    def __init__(
            self,
            name: str,
            recoil_pattern: List[RecoilData],
            length: int = 30,
            multiple: int = 6,
            sleep_divider: float = 6.0,
            sleep_suber: float = 0.0,
            game_sensitivity: float = 1.0,
            display_name: Optional[str] = None):
        """
        Initialize weapon profile.

        Args:
            name: Internal weapon name
            recoil_pattern: Raw recoil data (sensitivity already applied)
            length: Pattern length (points to use)
            multiple: Subdivision factor for smoothness
            sleep_divider: Timing divider
            sleep_suber: Timing adjustment
            game_sensitivity: Game sensitivity setting
            display_name: Display name for UI
        """
        self.name = name
        self.display_name = display_name or name
        self.length = length
        self.multiple = multiple
        self.sleep_divider = sleep_divider
        self.sleep_suber = sleep_suber
        self.game_sensitivity = game_sensitivity
        self.recoil_pattern = recoil_pattern
        self.calculated_pattern: List[RecoilData] = []

        self.logger = logging.getLogger(f"Weapon.{name}")
        self._calculate_pattern()

        self.logger.debug(
            "Weapon '%s' initialized with %s calculated points", name, len(self.calculated_pattern))

    def _calculate_pattern(self) -> None:
        """Calculate subdivided pattern using precise algorithm."""
        if not self.recoil_pattern:
            self.calculated_pattern = []
            return

        # Apply subdivision algorithm
        self.calculated_pattern = PatternSubdivisionAlgorithm.subdivide(
            self.recoil_pattern, self.multiple, self.length
        )

        # Validation logging
        self._validate_subdivision_precision()

    def _validate_subdivision_precision(self) -> None:
        """Validate subdivision maintains mathematical precision."""
        if not self.recoil_pattern or not self.calculated_pattern:
            return

        # Calculate expected vs actual sums
        pattern_to_process = self.recoil_pattern[:self.length]
        expected_sum_x = sum(p.dx for p in pattern_to_process)
        expected_sum_y = sum(p.dy for p in pattern_to_process)
        actual_sum_x = sum(p.dx for p in self.calculated_pattern)
        actual_sum_y = sum(p.dy for p in self.calculated_pattern)

        self.logger.debug(
            "Precision validation - X: expected=%.2f, actual=%.2f",
            expected_sum_x, actual_sum_x)
        self.logger.debug(
            "Precision validation - Y: expected=%.2f, actual=%.2f",
            expected_sum_y, actual_sum_y)

        # Alert on significant deviation
        if abs(
                expected_sum_x -
                actual_sum_x) > 1 or abs(
                expected_sum_y -
                actual_sum_y) > 1:
            self.logger.warning(
                "Significant deviation detected in subdivision calculation!")

    def recalculate_pattern(self) -> None:
        """Force recalculation of pattern after parameter changes."""
        self._calculate_pattern()
        self.logger.info(
            "Pattern recalculated: %s points", len(self.calculated_pattern))

    def update_sensitivity(
            self,
            new_sensitivity: float,
            csv_repository) -> bool:
        """
        Update sensitivity and reload pattern from CSV.

        Args:
            new_sensitivity: New game sensitivity
            csv_repository: Repository to reload CSV data

        Returns:
            True if update successful
        """
        try:
            csv_file = f"{self.name}.csv"
            new_recoil_data = csv_repository.load_weapon_pattern(
                csv_file, new_sensitivity)

            if new_recoil_data:
                self.recoil_pattern = new_recoil_data
                self.game_sensitivity = new_sensitivity
                self.recalculate_pattern()

                self.logger.info("Sensitivity updated: %s", new_sensitivity)
                return True
            else:
                self.logger.error(
                    "Failed to reload pattern for sensitivity update")
                return False

        except Exception as e:
            self.logger.error("Sensitivity update failed: %s", e)
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for serialization."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "length": self.length,
            "multiple": self.multiple,
            "sleep_divider": self.sleep_divider,
            "sleep_suber": self.sleep_suber,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any],
                  recoil_pattern: List[RecoilData]) -> 'WeaponProfile':
        """Create weapon profile from dictionary and pattern data."""
        return cls(
            name=data["name"],
            recoil_pattern=recoil_pattern,
            length=data.get("length", 30),
            multiple=data.get("multiple", 6),
            sleep_divider=data.get("sleep_divider", 6.0),
            sleep_suber=data.get("sleep_suber", 0.0),
            game_sensitivity=data.get("game_sensitivity", 1.0),
            display_name=data.get("display_name", data["name"])
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"WeaponProfile(name='{self.name}', "
                f"points={len(self.calculated_pattern)}, "
                f"multiple={self.multiple}, "
                f"sensitivity={self.game_sensitivity})")
