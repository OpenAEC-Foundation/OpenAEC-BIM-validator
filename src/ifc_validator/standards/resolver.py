"""Standards resolver for bundled IDS files.

This module provides the core logic for resolving shortcut names to bundled
IDS (Information Delivery Specification) file paths using importlib.resources.

The resolver supports the following Dutch BIM standards:
- nl-bim: NL_BIM Basis ILS v2 (Dutch baseline BIM information level specification)
- rvb: RVB BIM Norm v1.1 (Rijksvastgoedbedrijf Dutch Government Real Estate BIM norm)

Usage:
    from ifc_validator.standards.resolver import get_bundled_ids, is_shortcut

    # Check if a value is a shortcut
    if is_shortcut('nl-bim'):
        ids_path = get_bundled_ids('nl-bim')
"""

import sys
from importlib.resources import files
from pathlib import Path


# Mapping of shortcut names to bundled IDS filenames
STANDARD_SHORTCUTS: dict[str, str] = {
    'nl-bim': 'NL_BIM_Basis_ILS_v2.ids',
    'rvb': 'RVB_BIM_Norm_v1.1.ids',
}


def get_bundled_ids(shortcut: str) -> Path:
    """Resolve a shortcut name to the bundled IDS file path.

    This function uses importlib.resources to locate bundled IDS files,
    ensuring compatibility with both installed packages and development
    environments.

    Args:
        shortcut: The shortcut name for a bundled standard.
            Valid shortcuts: 'nl-bim', 'rvb'

    Returns:
        Path to the bundled IDS file that can be passed to ifctester.

    Raises:
        ValueError: If the shortcut is not recognized. The error message
            includes the list of valid shortcuts.
        FileNotFoundError: If the bundled IDS file is missing, which may
            indicate package corruption or incomplete installation.

    Examples:
        >>> path = get_bundled_ids('nl-bim')
        >>> str(path).endswith('NL_BIM_Basis_ILS_v2.ids')
        True

        >>> get_bundled_ids('invalid')
        Traceback (most recent call last):
            ...
        ValueError: Unknown standard shortcut: 'invalid'. Valid shortcuts are: nl-bim, rvb
    """
    if shortcut not in STANDARD_SHORTCUTS:
        valid_shortcuts = ', '.join(sorted(STANDARD_SHORTCUTS.keys()))
        raise ValueError(
            f"Unknown standard shortcut: '{shortcut}'. "
            f"Valid shortcuts are: {valid_shortcuts}"
        )

    filename = STANDARD_SHORTCUTS[shortcut]

    # When running as a PyInstaller frozen app, importlib.resources won't
    # work — resolve from the PyInstaller bundle directory instead.
    if getattr(sys, 'frozen', False):
        bundle_dir = Path(getattr(sys, '_MEIPASS', '.'))
        resource_path = bundle_dir / 'ifc_validator' / 'standards' / filename
        if not resource_path.exists():
            raise FileNotFoundError(
                f"Bundled IDS file not found in frozen app: {filename}. "
                f"Expected at: {resource_path}"
            )
        return resource_path

    standards_dir = files('ifc_validator.standards')
    resource = standards_dir / filename

    # Convert to Path for consistent interface
    # importlib.resources returns a Traversable, we need a concrete path
    # for ifctester compatibility (which requires str(path))
    try:
        resource_path = Path(str(resource))
        if not resource_path.exists():
            raise FileNotFoundError(
                f"Bundled IDS file not found: {filename}. "
                "The package may be corrupted or incompletely installed."
            )
        return resource_path
    except TypeError as e:
        # Handle case where resource is in a zip archive and can't be
        # directly converted to a path
        raise FileNotFoundError(
            f"Failed to access bundled IDS file: {filename}. "
            f"Error: {e}"
        ) from e


def is_shortcut(value: str) -> bool:
    """Check if a value is a recognized standard shortcut.

    This function is useful for CLI argument parsing to determine whether
    the user provided a shortcut name or a file path.

    Args:
        value: The value to check (e.g., from --ids argument)

    Returns:
        True if the value is a recognized shortcut ('nl-bim' or 'rvb'),
        False otherwise.

    Examples:
        >>> is_shortcut('nl-bim')
        True
        >>> is_shortcut('rvb')
        True
        >>> is_shortcut('/path/to/file.ids')
        False
        >>> is_shortcut('unknown')
        False
    """
    return value in STANDARD_SHORTCUTS


def list_available_standards() -> list[str]:
    """Get a list of all available standard shortcuts.

    Returns:
        List of available shortcut names that can be used with get_bundled_ids().

    Examples:
        >>> shortcuts = list_available_standards()
        >>> 'nl-bim' in shortcuts
        True
        >>> 'rvb' in shortcuts
        True
    """
    return list(STANDARD_SHORTCUTS.keys())


def get_standard_filename(shortcut: str) -> str:
    """Get the filename of a bundled standard without resolving the full path.

    This is useful for error messages and logging.

    Args:
        shortcut: The shortcut name for a bundled standard.

    Returns:
        The filename of the IDS file (e.g., 'NL_BIM_Basis_ILS_v2.ids')

    Raises:
        ValueError: If the shortcut is not recognized.
    """
    if shortcut not in STANDARD_SHORTCUTS:
        valid_shortcuts = ', '.join(sorted(STANDARD_SHORTCUTS.keys()))
        raise ValueError(
            f"Unknown standard shortcut: '{shortcut}'. "
            f"Valid shortcuts are: {valid_shortcuts}"
        )
    return STANDARD_SHORTCUTS[shortcut]


__all__ = [
    'STANDARD_SHORTCUTS',
    'get_bundled_ids',
    'get_standard_filename',
    'is_shortcut',
    'list_available_standards',
]
