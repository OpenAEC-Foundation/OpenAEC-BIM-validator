"""Core validation engine.

Re-exports all public names from the engine submodules:
- ``file_utils``: file validation functions and constants
- ``parser``: IFCParser, MemoryStats, load helpers
- ``validator``: validate() orchestration
"""

from ifc_validator.engine.file_utils import (
    IFC_MEMORY_EXPANSION_FACTOR,
    VALID_IDS_EXTENSIONS,
    VALID_IFC_EXTENSIONS,
    check_memory_available,
    get_memory_info,
    validate_file_exists,
    validate_ifc_extension,
    validate_ifc_file,
    validate_ids_extension,
    validate_ids_file,
)
from ifc_validator.engine.parser import (
    IFCParser,
    MemoryStats,
    load_ifc_model,
    load_ids_specification,
)
from ifc_validator.engine.validator import (
    validate,
)

__all__ = [
    # file_utils
    "VALID_IFC_EXTENSIONS",
    "VALID_IDS_EXTENSIONS",
    "IFC_MEMORY_EXPANSION_FACTOR",
    "validate_file_exists",
    "validate_ifc_extension",
    "validate_ids_extension",
    "check_memory_available",
    "get_memory_info",
    "validate_ifc_file",
    "validate_ids_file",
    # parser
    "IFCParser",
    "MemoryStats",
    "load_ifc_model",
    "load_ids_specification",
    # validator
    "validate",
]
