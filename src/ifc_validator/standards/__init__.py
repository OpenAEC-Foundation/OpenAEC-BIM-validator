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

    # Check if a value is a shortcut
    if is_shortcut('nl-bim'):
        ids_path = get_bundled_ids('nl-bim')

    # List available shortcuts
    print(list_available_standards())  # ['nl-bim', 'rvb']
"""

# Re-export from resolver module for public API
from ifc_validator.standards.resolver import (
    STANDARD_SHORTCUTS,
    get_bundled_ids,
    get_standard_filename,
    is_shortcut,
    list_available_standards,
)

__all__ = [
    'STANDARD_SHORTCUTS',
    'get_bundled_ids',
    'get_standard_filename',
    'is_shortcut',
    'list_available_standards',
]
