"""Backward compatibility shim.

All code has been refactored into ``ifc_validator.models`` and
``ifc_validator.engine``. This module re-exports every public name
so that existing ``from ifc_validator.validator import X`` imports
continue to work.
"""

# Models
# Engine — file utilities
from ifc_validator.engine.file_utils import (  # noqa: F401
    IFC_MEMORY_EXPANSION_FACTOR,
    VALID_IDS_EXTENSIONS,
    VALID_IFC_EXTENSIONS,
    check_memory_available,
    get_memory_info,
    validate_file_exists,
    validate_ids_extension,
    validate_ids_file,
    validate_ifc_extension,
    validate_ifc_file,
)

# Engine — parser
from ifc_validator.engine.parser import (  # noqa: F401
    load_ids_specification,
    load_ifc_model,
)

# Engine — validator
from ifc_validator.engine.validator import (  # noqa: F401
    _extract_entity_failure,
    validate,
)
from ifc_validator.models import (  # noqa: F401
    EntityFailure,
    SpecificationResult,
    ValidationResult,
)
