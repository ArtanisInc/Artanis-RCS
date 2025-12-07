"""
Weapon profile model with recoil pattern subdivision algorithm.
"""
import logging
from typing import List, Dict, Any, Optional

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

        # Process each original point
        for point in pattern_to_process:
            # Calculate precise subdivision values
            base_dx = point.dx / multiple
            base_dy = point.dy / multiple

            # Track fractional parts for precise distribution
            remaining_dx = point.dx
            remaining_dy = point.dy

            # Subdivide current point
            for j in range(multiple):
                if j == multiple - 1:
                    # Last subdivision gets remaining value for exact precision
                    sub_dx = remaining_dx
                    sub_dy = remaining_dy
                else:
                    # Use precise floating-point division
                    sub_dx = base_dx
                    sub_dy = base_dy
                    remaining_dx -= base_dx
                    remaining_dy -= base_dy

                result.append(RecoilData(
                    dx=sub_dx,
                    dy=sub_dy,
                    delay=point.delay
                ))

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
            display_name: Optional[str] = None,
            jitter_timing: float = 0.0,
            jitter_movement: float = 0.0):
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
            jitter_timing: Random timing variation (+/- milliseconds)
            jitter_movement: Random movement variation (+/- percentage, 0-100)
        """
        self.name = name
        self.display_name = display_name or name
        self.length = length
        self.multiple = multiple
        self.sleep_divider = sleep_divider
        self.sleep_suber = sleep_suber
        self.game_sensitivity = game_sensitivity
        self.jitter_timing = jitter_timing
        self.jitter_movement = jitter_movement
        self.recoil_pattern = recoil_pattern
        self.calculated_pattern: List[RecoilData] = []

        self.logger = logging.getLogger(f"Weapon.{name}")
        self._calculate_pattern()

        self.logger.debug(
            f"Weapon '{name}' initialized with {len(self.calculated_pattern)} calculated points")

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
            f"Pattern recalculated: {len(self.calculated_pattern)} points")

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

                self.logger.info(f"Sensitivity updated: {new_sensitivity}")
                return True
            else:
                self.logger.error(
                    "Failed to reload pattern for sensitivity update")
                return False

        except Exception as e:
            self.logger.error(f"Sensitivity update failed: {e}")
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
            "jitter_timing": self.jitter_timing,
            "jitter_movement": self.jitter_movement,
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
            display_name=data.get("display_name", data["name"]),
            jitter_timing=data.get("jitter_timing", 0.0),
            jitter_movement=data.get("jitter_movement", 0.0)
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"WeaponProfile(name='{self.name}', "
                f"points={len(self.calculated_pattern)}, "
                f"multiple={self.multiple}, "
                f"sensitivity={self.game_sensitivity})")