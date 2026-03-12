"""Backward compatibility shim.

IFCParser and MemoryStats have been moved to
``ifc_validator.engine.parser``. This module re-exports them so that
existing ``from src.ifc_parser import IFCParser`` imports continue
to work.
"""

from ifc_validator.engine.parser import IFCParser, MemoryStats  # noqa: F401

__all__ = ["IFCParser", "MemoryStats"]
