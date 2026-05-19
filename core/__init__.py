"""Core package index for surveillance components."""

from .config import SURVEILLANCE_CONFIG_PATH

__all__ = ["SURVEILLANCE_CONFIG_PATH"]
"""Core package: runtime engine and orchestration."""

__all__ = [
    "surveillance_engine",
    "multi_source_coordinator",
    "surveillance_orchestrator",
]
