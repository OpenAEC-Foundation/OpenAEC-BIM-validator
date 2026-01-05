"""Bundled IDS standards for IFC validation.

This package contains bundled Information Delivery Specification (IDS) files
for Dutch BIM standards, enabling validation without external IDS files.

Bundled Standards:
- NL_BIM Basis ILS v2: Dutch baseline BIM information level specification
- RVB BIM Norm v1.1: Rijksvastgoedbedrijf (Dutch Government Real Estate) BIM norm

Usage:
    from ifc_validator.standards import get_bundled_ids, STANDARD_SHORTCUTS

    # Get path to bundled IDS file
    ids_path = get_bundled_ids('nl-bim')
    ids_path = get_bundled_ids('rvb')

    # Check available shortcuts
    print(STANDARD_SHORTCUTS.keys())  # ['nl-bim', 'rvb']
"""

from importlib.resources import files
from pathlib import Path
from typing import Union

# Mapping of shortcut names to bundled IDS filenames
STANDARD_SHORTCUTS = {
    'nl-bim': 'NL_BIM_Basis_ILS_v2.ids',
    'rvb': 'RVB_BIM_Norm_v1.1.ids',
}


def get_bundled_ids(shortcut: str) -> Path:
    """Resolve a shortcut name to the bundled IDS file path.

    Args:
        shortcut: The shortcut name for a bundled standard ('nl-bim' or 'rvb')

    Returns:
        Path to the bundled IDS file

    Raises:
        ValueError: If the shortcut is not recognized
        FileNotFoundError: If the bundled IDS file is missing (package corruption)
    """
    if shortcut not in STANDARD_SHORTCUTS:
        valid_shortcuts = ', '.join(sorted(STANDARD_SHORTCUTS.keys()))
        raise ValueError(
            f"Unknown standard shortcut: '{shortcut}'. "
            f"Valid shortcuts are: {valid_shortcuts}"
        )

    filename = STANDARD_SHORTCUTS[shortcut]
    standards_dir = files('ifc_validator.standards')
    resource = standards_dir / filename

    # Convert to Path for consistent interface
    # Use as_file context manager for resources that may be in zip archives
    try:
        # For development/installed packages, this gives us a traversable path
        resource_path = Path(str(resource))
        if not resource_path.exists():
            raise FileNotFoundError(
                f"Bundled IDS file not found: {filename}. "
                "The package may be corrupted or incompletely installed."
            )
        return resource_path
    except Exception as e:
        raise FileNotFoundError(
            f"Failed to access bundled IDS file: {filename}. "
            f"Error: {e}"
        ) from e


def is_shortcut(value: str) -> bool:
    """Check if a value is a recognized standard shortcut.

    Args:
        value: The value to check

    Returns:
        True if the value is a recognized shortcut, False otherwise
    """
    return value in STANDARD_SHORTCUTS


def list_available_standards() -> list[str]:
    """Get a list of all available standard shortcuts.

    Returns:
        List of available shortcut names
    """
    return list(STANDARD_SHORTCUTS.keys())


__all__ = [
    'STANDARD_SHORTCUTS',
    'get_bundled_ids',
    'is_shortcut',
    'list_available_standards',
]
