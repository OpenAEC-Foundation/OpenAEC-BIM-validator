"""Validation utilities for IFC and IDS files.

This module provides file validation functions including:
- File existence checks
- Extension validation for IFC (.ifc, .ifcxml, .ifczip) and IDS (.ids) files
- Memory preflight checks using psutil with 10x file size heuristic

Usage:
    from ifc_validator.validator import (
        validate_ifc_file,
        validate_ids_file,
        check_memory_available,
    )

    # Validate and load IFC file
    ifc_path = validate_ifc_file("/path/to/model.ifc")

    # Check memory before loading
    if not check_memory_available(ifc_path):
        raise MemoryError("Insufficient memory")
"""

from pathlib import Path
from typing import Union

import psutil


# Valid file extensions
VALID_IFC_EXTENSIONS = {".ifc", ".ifcxml", ".ifczip"}
VALID_IDS_EXTENSIONS = {".ids"}

# Memory expansion factor for IFC files when loaded into memory
IFC_MEMORY_EXPANSION_FACTOR = 10


def validate_file_exists(file_path: Union[str, Path], file_type: str = "File") -> Path:
    """Validate that a file exists and return a Path object.

    Args:
        file_path: Path to the file (string or Path object)
        file_type: Description of file type for error messages (e.g., "IFC", "IDS")

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: If the file does not exist
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"{file_type} file not found: {file_path}")

    if not path.is_file():
        raise FileNotFoundError(f"{file_type} path is not a file: {file_path}")

    return path


def validate_ifc_extension(file_path: Union[str, Path]) -> Path:
    """Validate that a file has a valid IFC extension.

    Valid extensions: .ifc, .ifcxml, .ifczip

    Args:
        file_path: Path to the file

    Returns:
        Path object for the validated file

    Raises:
        ValueError: If the file has an invalid extension
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension not in VALID_IFC_EXTENSIONS:
        valid_exts = ", ".join(sorted(VALID_IFC_EXTENSIONS))
        raise ValueError(
            f"Invalid IFC file extension: '{extension}'. "
            f"Valid extensions are: {valid_exts}"
        )

    return path


def validate_ids_extension(file_path: Union[str, Path]) -> Path:
    """Validate that a file has a valid IDS extension.

    Valid extensions: .ids

    Args:
        file_path: Path to the file

    Returns:
        Path object for the validated file

    Raises:
        ValueError: If the file has an invalid extension
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension not in VALID_IDS_EXTENSIONS:
        valid_exts = ", ".join(sorted(VALID_IDS_EXTENSIONS))
        raise ValueError(
            f"Invalid IDS file extension: '{extension}'. "
            f"Valid extensions are: {valid_exts}"
        )

    return path


def check_memory_available(file_path: Union[str, Path]) -> bool:
    """Check if sufficient memory is available to load an IFC file.

    IFC files expand approximately 10x when loaded into memory.
    This function checks if available system memory exceeds the
    estimated memory requirement.

    Args:
        file_path: Path to the IFC file

    Returns:
        True if sufficient memory is available, False otherwise
    """
    path = Path(file_path)

    if not path.exists():
        return False

    file_size = path.stat().st_size
    available_memory = psutil.virtual_memory().available
    required_memory = file_size * IFC_MEMORY_EXPANSION_FACTOR

    return available_memory > required_memory


def get_memory_info(file_path: Union[str, Path]) -> dict:
    """Get detailed memory information for loading a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file_size, available_memory, required_memory,
        and is_sufficient fields
    """
    path = Path(file_path)

    if not path.exists():
        return {
            "file_size": 0,
            "available_memory": psutil.virtual_memory().available,
            "required_memory": 0,
            "is_sufficient": False,
            "error": "File does not exist",
        }

    file_size = path.stat().st_size
    available_memory = psutil.virtual_memory().available
    required_memory = file_size * IFC_MEMORY_EXPANSION_FACTOR

    return {
        "file_size": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "available_memory": available_memory,
        "available_memory_mb": round(available_memory / (1024 * 1024), 2),
        "required_memory": required_memory,
        "required_memory_mb": round(required_memory / (1024 * 1024), 2),
        "is_sufficient": available_memory > required_memory,
    }


def validate_ifc_file(file_path: Union[str, Path]) -> Path:
    """Validate an IFC file: check existence, extension, and memory.

    Performs validation in order:
    1. Check file exists
    2. Validate extension (.ifc, .ifcxml, .ifczip)
    3. Check memory availability

    Args:
        file_path: Path to the IFC file

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file has invalid extension
        MemoryError: If insufficient memory available
    """
    # Check existence
    path = validate_file_exists(file_path, "IFC")

    # Check extension
    validate_ifc_extension(path)

    # Check memory
    if not check_memory_available(path):
        memory_info = get_memory_info(path)
        raise MemoryError(
            f"Insufficient memory to load IFC file. "
            f"File size: {memory_info['file_size_mb']:.1f} MB, "
            f"Required: ~{memory_info['required_memory_mb']:.1f} MB, "
            f"Available: {memory_info['available_memory_mb']:.1f} MB"
        )

    return path


def validate_ids_file(file_path: Union[str, Path]) -> Path:
    """Validate an IDS file: check existence and extension.

    Performs validation in order:
    1. Check file exists
    2. Validate extension (.ids)

    Args:
        file_path: Path to the IDS file

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file has invalid extension
    """
    # Check existence
    path = validate_file_exists(file_path, "IDS")

    # Check extension
    validate_ids_extension(path)

    return path
