"""
Data package for repositories and data access layer.
"""

from .config_repository import ConfigRepository, CSVRepository

__all__ = [
    'ConfigRepository',
    'CSVRepository'
]
