"""IFC/IDS file parsing utilities.

This module provides:
- ``IFCParser`` class for loading and querying IFC files with memory tracking.
- ``MemoryStats`` dataclass for memory usage statistics.
- ``load_ifc_model()`` / ``load_ids_specification()`` convenience functions.

No ifc_validator imports — this is a leaf module.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

import ifcopenshell
import psutil
from ifctester import ids


@dataclass
class MemoryStats:
    """Memory usage statistics for IFC file loading.

    Tracks memory consumption before and after loading an IFC file,
    providing insights into the actual memory footprint of parsed files.

    Attributes:
        memory_before: Process RSS memory (bytes) before loading.
        memory_after: Process RSS memory (bytes) after loading.
        file_size: Size of the IFC file on disk (bytes).
    """

    memory_before: int
    memory_after: int
    file_size: int

    @property
    def memory_used(self) -> int:
        """Calculate memory consumed by loading the file.

        Returns:
            Memory consumed in bytes (memory_after - memory_before).
        """
        return self.memory_after - self.memory_before

    @property
    def memory_multiplier(self) -> float:
        """Calculate actual memory usage as a multiplier of file size.

        Returns:
            Ratio of memory_used to file_size, or 0.0 if file_size is zero.
        """
        if self.file_size == 0:
            return 0.0
        return self.memory_used / self.file_size

    def __repr__(self) -> str:
        """Return human-readable string representation."""
        used_mb = self.memory_used / (1024 * 1024)
        file_mb = self.file_size / (1024 * 1024)
        return (
            f"MemoryStats(used={used_mb:.2f}MB, "
            f"file_size={file_mb:.2f}MB, "
            f"multiplier={self.memory_multiplier:.1f}x)"
        )


class IFCParser:
    """IFC file parser using IfcOpenShell.

    Provides memory-efficient loading of IFC2X3, IFC4, and IFC4X3 files
    with comprehensive error handling for corrupt or malformed files.

    Attributes:
        file_path: Path to the currently loaded IFC file.
        schema: The IFC schema version (e.g., 'IFC2X3', 'IFC4').
        ifc_file: The underlying IfcOpenShell file object.
    """

    SUPPORTED_SCHEMAS = ("IFC2X3", "IFC4", "IFC4X3")
    VALID_EXTENSIONS = (".ifc", ".ifcxml", ".ifczip")
    MEMORY_MULTIPLIER = 10

    def __init__(self) -> None:
        """Initialize the IFC parser with default state."""
        self._file_path: Optional[Path] = None
        self._schema: Optional[str] = None
        self._ifc_file: Optional[Any] = None
        self._memory_stats: Optional[MemoryStats] = None
        self._process = psutil.Process(os.getpid())

    @property
    def file_path(self) -> Optional[Path]:
        """Get the path to the currently loaded IFC file."""
        return self._file_path

    @property
    def schema(self) -> Optional[str]:
        """Get the IFC schema version of the loaded file."""
        return self._schema

    @property
    def ifc_file(self) -> Optional[Any]:
        """Get the underlying IfcOpenShell file object."""
        return self._ifc_file

    @property
    def is_loaded(self) -> bool:
        """Check if an IFC file is currently loaded."""
        return self._ifc_file is not None

    @property
    def memory_stats(self) -> Optional[MemoryStats]:
        """Get memory statistics from the most recent file load."""
        return self._memory_stats

    def _get_memory_rss(self) -> int:
        """Get current process RSS memory usage in bytes."""
        return self._process.memory_info().rss

    def _format_parse_error(self, file_path: str, error_msg: str) -> str:
        """Format a parse error message with helpful context.

        Args:
            file_path: Path to the file that failed to parse.
            error_msg: The raw error message from IfcOpenShell.

        Returns:
            A formatted error message with context and suggestions.
        """
        error_patterns = {
            "Unable to parse IFC SPF header": (
                "The file header is missing or malformed. "
                "IFC files must start with 'ISO-10303-21;' followed "
                "by a valid HEADER section."
            ),
            "Unexpected token": (
                "The file contains invalid STEP syntax. "
                "Check for malformed entity definitions or "
                "unexpected characters."
            ),
            "syntax error": (
                "The file contains STEP syntax errors. "
                "The file may be truncated or contain invalid data."
            ),
            "Duplicate id": (
                "The file contains duplicate entity IDs. "
                "Each #ID reference must be unique within the file."
            ),
            "Invalid entity": (
                "The file contains an invalid or unknown entity type. "
                "This may indicate file corruption or schema "
                "incompatibility."
            ),
            "Unknown entity": (
                "The file references an entity type not defined in "
                "the schema. Check that the file schema matches the "
                "declared FILE_SCHEMA."
            ),
        }

        error_lower = error_msg.lower()
        for pattern, description in error_patterns.items():
            if pattern.lower() in error_lower:
                return (
                    f"Failed to parse IFC file '{file_path}': "
                    f"{error_msg}. {description}"
                )

        return (
            f"Failed to parse IFC file '{file_path}': {error_msg}. "
            "The file may be corrupt, truncated, or contain invalid "
            "STEP/IFC data."
        )

    def _check_memory_constraint(
        self,
        file_path: str,
        multiplier: Optional[int] = None,
    ) -> None:
        """Verify that sufficient memory is available to load the IFC file.

        Args:
            file_path: Path to the IFC file to check.
            multiplier: Optional memory multiplier override.

        Raises:
            FileNotFoundError: If the file does not exist.
            MemoryError: If insufficient memory is available.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"IFC file not found: {file_path}")

        file_size = path.stat().st_size
        mem_multiplier = (
            multiplier if multiplier is not None else self.MEMORY_MULTIPLIER
        )
        required_memory = file_size * mem_multiplier
        available_memory = psutil.virtual_memory().available

        if required_memory > available_memory:
            file_size_gb = file_size / (1024**3)
            required_gb = required_memory / (1024**3)
            available_gb = available_memory / (1024**3)

            raise MemoryError(
                f"Insufficient memory to load IFC file '{file_path}': "
                f"file size is {file_size_gb:.2f}GB, "
                f"estimated memory requirement is ~{required_gb:.2f}GB "
                f"({mem_multiplier}x file size), "
                f"but only {available_gb:.2f}GB is available."
            )

    def load(self, file_path: str) -> None:
        """Load an IFC file from the specified path.

        Args:
            file_path: Path to the IFC file to load.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file extension is invalid, file is empty,
                or parsing fails.
            PermissionError: If the file cannot be read.
            IsADirectoryError: If the path points to a directory.
            MemoryError: If insufficient memory is available.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"IFC file not found: {file_path}")

        if path.is_dir():
            raise IsADirectoryError(
                f"Path is a directory, not a file: {file_path}"
            )

        try:
            with open(path, "rb") as f:
                f.read(1)
        except PermissionError as e:
            raise PermissionError(
                f"Permission denied: cannot read file: {file_path}"
            ) from e
        except OSError as e:
            raise OSError(
                f"Cannot access file: {file_path}. Error: {e}"
            ) from e

        file_size = path.stat().st_size
        if file_size == 0:
            raise ValueError(f"IFC file is empty (0 bytes): {file_path}")

        if path.suffix.lower() not in self.VALID_EXTENSIONS:
            raise ValueError(
                f"Invalid file extension '{path.suffix}'. "
                f"Supported extensions: {', '.join(self.VALID_EXTENSIONS)}"
            )

        self._check_memory_constraint(file_path)

        if self.is_loaded:
            self.close()

        memory_before = self._get_memory_rss()

        try:
            self._ifc_file = ifcopenshell.open(str(path))
        except MemoryError as e:
            raise MemoryError(
                f"Insufficient memory to load IFC file: {file_path}"
            ) from e
        except ifcopenshell.SchemaError as e:
            raise ValueError(
                f"IFC schema error in '{file_path}': {e}. "
                "The file may use an unsupported or malformed "
                "schema definition."
            ) from e
        except ifcopenshell.Error as e:
            error_msg = str(e)
            raise ValueError(
                self._format_parse_error(file_path, error_msg)
            ) from e
        except RuntimeError as e:
            raise ValueError(
                f"Failed to parse IFC file '{file_path}': {e}. "
                "The file may be corrupt or contain invalid "
                "STEP syntax."
            ) from e
        except Exception as e:
            raise ValueError(
                f"Unexpected error parsing IFC file '{file_path}': "
                f"{type(e).__name__}: {e}"
            ) from e

        memory_after = self._get_memory_rss()

        self._memory_stats = MemoryStats(
            memory_before=memory_before,
            memory_after=memory_after,
            file_size=file_size,
        )

        self._file_path = path
        self._schema = self._ifc_file.schema

        if self._schema not in self.SUPPORTED_SCHEMAS:
            schema = self._schema
            self.close()
            raise ValueError(
                f"Unsupported IFC schema '{schema}'. "
                f"Supported schemas: {', '.join(self.SUPPORTED_SCHEMAS)}"
            )

    def close(self) -> None:
        """Close the currently loaded IFC file and free resources."""
        self._ifc_file = None
        self._file_path = None
        self._schema = None

    def get_entities_by_type(self, entity_type: str) -> list[Any]:
        """Get all entities of a specific type from the loaded IFC file.

        Args:
            entity_type: The IFC entity type (e.g., 'IfcWall', 'IfcDoor').

        Returns:
            List of entities matching the specified type.

        Raises:
            RuntimeError: If no file is currently loaded.
        """
        if not self.is_loaded:
            raise RuntimeError("No IFC file is currently loaded")
        return list(self._ifc_file.by_type(entity_type))

    def __enter__(self) -> "IFCParser":
        """Enter the context manager."""
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """Exit the context manager and close the file."""
        self.close()

    def __repr__(self) -> str:
        """Return a string representation of the parser."""
        if self.is_loaded:
            return (
                f"IFCParser(file='{self._file_path}', "
                f"schema='{self._schema}')"
            )
        return "IFCParser(not loaded)"


# -------------------------------------------------------------------------
# Convenience functions
# -------------------------------------------------------------------------


def load_ifc_model(file_path: Union[str, Path]) -> ifcopenshell.file:
    """Load an IFC model from file.

    Args:
        file_path: Path to the IFC file.

    Returns:
        Loaded IFC model.

    Raises:
        RuntimeError: If the file cannot be parsed.
    """
    try:
        return ifcopenshell.open(str(file_path))
    except Exception as e:
        raise RuntimeError(f"Failed to parse IFC file: {e}") from e


def load_ids_specification(file_path: Union[str, Path]):
    """Load an IDS specification from file.

    Args:
        file_path: Path to the IDS file.

    Returns:
        Loaded IDS specification object.

    Raises:
        RuntimeError: If the file cannot be parsed.
    """
    try:
        return ids.open(str(file_path))
    except Exception as e:
        raise RuntimeError(f"Failed to parse IDS file: {e}") from e
