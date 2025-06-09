"""
Recoil compensation data model.
"""
from dataclasses import dataclass


@dataclass
class RecoilData:
    """Represents a single recoil compensation point."""

    dx: float  # Horizontal displacement
    dy: float  # Vertical displacement
    delay: float  # Timing delay in milliseconds
