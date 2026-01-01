"""
IFC Parser Module - Core parsing functionality for IFC files.

This module provides the IFCParser class for loading and parsing IFC files
using IfcOpenShell. It supports IFC2X3, IFC4, and IFC4X3 schemas with
memory-efficient handling for large files (up to 1GB).

Supported Schemas:
    - IFC2X3: Industry Foundation Classes version 2x3
    - IFC4: Industry Foundation Classes version 4
    - IFC4X3: Industry Foundation Classes version 4x3

Supported Extensions:
    - .ifc: Standard STEP Physical File format
    - .ifcxml: XML-based IFC format
    - .ifczip: Compressed IFC archive

Usage Examples:

    Basic Loading
    -------------
    Load an IFC file and access its properties:

        from src.ifc_parser import IFCParser

        parser = IFCParser()
        parser.load('path/to/model.ifc')

        # Check if file is loaded
        print(parser.is_loaded)  # True

        # Get the schema version
        print(parser.schema)  # 'IFC2X3', 'IFC4', or 'IFC4X3'

        # Get the file path
        print(parser.file_path)  # PosixPath('path/to/model.ifc')

        # Access underlying IfcOpenShell file object for advanced operations
        ifc_file = parser.ifc_file
        project = ifc_file.by_type('IfcProject')[0]

        # Clean up when done
        parser.close()

    Context Manager (Recommended)
    -----------------------------
    Use the context manager for automatic resource cleanup:

        from src.ifc_parser import IFCParser

        with IFCParser() as parser:
            parser.load('path/to/model.ifc')

            # Query entities by type
            walls = parser.get_entities_by_type('IfcWall')
            print(f"Found {len(walls)} walls")

            doors = parser.get_entities_by_type('IfcDoor')
            print(f"Found {len(doors)} doors")

        # File automatically closed when exiting the 'with' block

    Entity Querying
    ---------------
    Query specific entity types from the loaded model:

        with IFCParser() as parser:
            parser.load('building.ifc')

            # Get all walls
            walls = parser.get_entities_by_type('IfcWall')

            # Get all spaces
            spaces = parser.get_entities_by_type('IfcSpace')

            # Get building storeys
            storeys = parser.get_entities_by_type('IfcBuildingStorey')

            # Process entities
            for wall in walls:
                print(f"Wall: {wall.Name}, GUID: {wall.GlobalId}")

    Memory Monitoring
    -----------------
    Monitor memory usage when loading large files:

        from src.ifc_parser import IFCParser

        parser = IFCParser()
        parser.load('large_model.ifc')

        # Access memory statistics
        stats = parser.memory_stats

        # Memory consumed by loading (in bytes)
        print(f"Memory used: {stats.memory_used / 1024 / 1024:.2f} MB")

        # Original file size on disk
        print(f"File size: {stats.file_size / 1024 / 1024:.2f} MB")

        # Memory expansion factor (typically ~10x for IFC files)
        print(f"Memory multiplier: {stats.memory_multiplier:.1f}x file size")

        # Full stats representation
        print(stats)  # MemoryStats(used=68.50MB, file_size=6.87MB, multiplier=10.0x)

        parser.close()

    Error Handling
    --------------
    Handle various error conditions when loading files:

        from src.ifc_parser import IFCParser

        parser = IFCParser()

        try:
            parser.load('model.ifc')
        except FileNotFoundError as e:
            # File does not exist
            print(f"File not found: {e}")
        except IsADirectoryError as e:
            # Path points to a directory, not a file
            print(f"Not a file: {e}")
        except PermissionError as e:
            # Cannot read the file (access denied)
            print(f"Permission denied: {e}")
        except MemoryError as e:
            # Insufficient memory to load the file (10x file size required)
            print(f"Not enough memory: {e}")
        except ValueError as e:
            # Invalid file: empty, wrong extension, corrupt, or unsupported schema
            print(f"Invalid IFC file: {e}")

    Comprehensive Error Handling Pattern
    ------------------------------------
    Production-ready error handling with logging:

        import logging
        from src.ifc_parser import IFCParser

        logger = logging.getLogger(__name__)

        def load_ifc_safely(file_path: str) -> IFCParser | None:
            '''Load an IFC file with comprehensive error handling.'''
            parser = IFCParser()

            try:
                parser.load(file_path)
                logger.info(f"Loaded {file_path} (schema: {parser.schema})")
                return parser

            except FileNotFoundError:
                logger.error(f"IFC file not found: {file_path}")
            except IsADirectoryError:
                logger.error(f"Path is a directory, not a file: {file_path}")
            except PermissionError:
                logger.error(f"Cannot read file (permission denied): {file_path}")
            except MemoryError as e:
                logger.error(f"Insufficient memory to load file: {e}")
            except ValueError as e:
                logger.error(f"Failed to parse IFC file: {e}")

            return None

    Loading Multiple Files
    ----------------------
    Load multiple files sequentially (close each before opening the next):

        from src.ifc_parser import IFCParser

        files = ['model_a.ifc', 'model_b.ifc', 'model_c.ifc']
        results = {}

        parser = IFCParser()
        for file_path in files:
            try:
                parser.load(file_path)  # Automatically closes previous file
                results[file_path] = {
                    'schema': parser.schema,
                    'walls': len(parser.get_entities_by_type('IfcWall')),
                    'memory_mb': parser.memory_stats.memory_used / 1024 / 1024,
                }
            except (FileNotFoundError, ValueError) as e:
                results[file_path] = {'error': str(e)}

        parser.close()

Note:
    The parser is NOT thread-safe. Each thread should use its own IFCParser
    instance when loading files concurrently.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import ifcopenshell
import psutil


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

        This indicates how much memory expansion occurred when parsing
        the IFC file. A multiplier of 10.0x means the in-memory
        representation uses 10 times the disk file size.

        Returns:
            Ratio of memory_used to file_size, or 0.0 if file_size is zero.
        """
        if self.file_size == 0:
            return 0.0
        return self.memory_used / self.file_size

    def __repr__(self) -> str:
        """Return human-readable string representation.

        Returns:
            Formatted string showing memory used, file size, and multiplier
            in megabytes.
        """
        used_mb = self.memory_used / (1024 * 1024)
        file_mb = self.file_size / (1024 * 1024)
        return (
            f"MemoryStats(used={used_mb:.2f}MB, "
            f"file_size={file_mb:.2f}MB, "
            f"multiplier={self.memory_multiplier:.1f}x)"
        )


class IFCParser:
    """
    IFC file parser using IfcOpenShell.

    Provides memory-efficient loading of IFC2X3 and IFC4 files with
    comprehensive error handling for corrupt or malformed files.

    Attributes:
        file_path: Path to the currently loaded IFC file.
        schema: The IFC schema version (e.g., 'IFC2X3', 'IFC4').
        ifc_file: The underlying IfcOpenShell file object.

    Example:
        >>> parser = IFCParser()
        >>> parser.load('model.ifc')
        >>> print(parser.schema)
        'IFC4'
    """

    # Supported IFC schema versions
    SUPPORTED_SCHEMAS = ("IFC2X3", "IFC4", "IFC4X3")

    # Valid IFC file extensions
    VALID_EXTENSIONS = (".ifc", ".ifcxml", ".ifczip")

    # Memory multiplier for file size constraint
    # IFC files typically expand to ~10x their size in memory when parsed
    MEMORY_MULTIPLIER = 10

    def __init__(self) -> None:
        """Initialize the IFC parser with default state.

        Creates a new parser instance with no file loaded. The parser
        tracks memory usage during file loading and provides access
        to the underlying IfcOpenShell file object.

        Example:
            >>> parser = IFCParser()
            >>> parser.is_loaded
            False
        """
        self._file_path: Optional[Path] = None
        self._schema: Optional[str] = None
        self._ifc_file: Optional[Any] = None
        self._memory_stats: Optional[MemoryStats] = None
        self._process = psutil.Process(os.getpid())

    @property
    def file_path(self) -> Optional[Path]:
        """Get the path to the currently loaded IFC file.

        Returns:
            Path object pointing to the loaded file, or None if no file
            is currently loaded.
        """
        return self._file_path

    @property
    def schema(self) -> Optional[str]:
        """Get the IFC schema version of the loaded file.

        Returns:
            Schema identifier string (e.g., 'IFC2X3', 'IFC4', 'IFC4X3'),
            or None if no file is currently loaded.
        """
        return self._schema

    @property
    def ifc_file(self) -> Optional[Any]:
        """Get the underlying IfcOpenShell file object.

        Provides direct access to the ifcopenshell.file object for
        advanced operations not exposed by IFCParser methods.

        Returns:
            The ifcopenshell.file object, or None if no file is loaded.
        """
        return self._ifc_file

    @property
    def is_loaded(self) -> bool:
        """Check if an IFC file is currently loaded.

        Returns:
            True if a file is loaded and available for queries,
            False otherwise.
        """
        return self._ifc_file is not None

    @property
    def memory_stats(self) -> Optional[MemoryStats]:
        """Get memory statistics from the most recent file load.

        Returns:
            MemoryStats object containing before/after memory usage,
            or None if no file has been loaded.
        """
        return self._memory_stats

    def _get_memory_rss(self) -> int:
        """Get current process RSS memory usage in bytes.

        Uses psutil to query the Resident Set Size (RSS) memory,
        which represents the actual physical memory used by the process.

        Returns:
            Current RSS memory usage in bytes.
        """
        return self._process.memory_info().rss

    def _format_parse_error(self, file_path: str, error_msg: str) -> str:
        """
        Format a parse error message with helpful context.

        Analyzes the error message from IfcOpenShell and provides
        user-friendly descriptions of common corruption issues.

        Args:
            file_path: Path to the file that failed to parse.
            error_msg: The raw error message from IfcOpenShell.

        Returns:
            A formatted error message with context and suggestions.
        """
        # Common error patterns and their user-friendly descriptions
        error_patterns = {
            "Unable to parse IFC SPF header": (
                "The file header is missing or malformed. "
                "IFC files must start with 'ISO-10303-21;' followed by a valid HEADER section."
            ),
            "Unexpected token": (
                "The file contains invalid STEP syntax. "
                "Check for malformed entity definitions or unexpected characters."
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
                "This may indicate file corruption or schema incompatibility."
            ),
            "Unknown entity": (
                "The file references an entity type not defined in the schema. "
                "Check that the file schema matches the declared FILE_SCHEMA."
            ),
        }

        # Find matching pattern
        error_lower = error_msg.lower()
        for pattern, description in error_patterns.items():
            if pattern.lower() in error_lower:
                return (
                    f"Failed to parse IFC file '{file_path}': {error_msg}. "
                    f"{description}"
                )

        # Default message for unrecognized errors
        return (
            f"Failed to parse IFC file '{file_path}': {error_msg}. "
            "The file may be corrupt, truncated, or contain invalid STEP/IFC data."
        )

    def _check_memory_constraint(
        self, file_path: str, multiplier: Optional[int] = None
    ) -> None:
        """
        Verify that sufficient memory is available to load the IFC file.

        IFC files typically expand to approximately 10x their on-disk size
        when fully parsed into memory. This method checks available system
        memory against the estimated requirement before attempting to load.

        Args:
            file_path: Path to the IFC file to check.
            multiplier: Optional memory multiplier override (default: MEMORY_MULTIPLIER).

        Raises:
            FileNotFoundError: If the file does not exist.
            MemoryError: If insufficient memory is available to safely load the file.
        """
        path = Path(file_path)

        # Ensure file exists before checking size
        if not path.exists():
            raise FileNotFoundError(f"IFC file not found: {file_path}")

        # Get file size in bytes
        file_size = path.stat().st_size

        # Use provided multiplier or class default
        mem_multiplier = (
            multiplier if multiplier is not None else self.MEMORY_MULTIPLIER
        )

        # Calculate required memory estimate
        required_memory = file_size * mem_multiplier

        # Get available system memory
        available_memory = psutil.virtual_memory().available

        # Check if sufficient memory is available
        if required_memory > available_memory:
            # Format sizes for human-readable error message
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
        """
        Load an IFC file from the specified path.

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
        # Convert to Path object for validation
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"IFC file not found: {file_path}")

        # Check if path is a file (not a directory)
        if path.is_dir():
            raise IsADirectoryError(f"Path is a directory, not a file: {file_path}")

        # Check file accessibility (readable)
        try:
            with open(path, "rb") as f:
                # Read a small amount to verify accessibility
                f.read(1)
        except PermissionError as e:
            raise PermissionError(
                f"Permission denied: cannot read file: {file_path}"
            ) from e
        except OSError as e:
            raise OSError(f"Cannot access file: {file_path}. Error: {e}") from e

        # Check for zero-byte (empty) files
        file_size = path.stat().st_size
        if file_size == 0:
            raise ValueError(f"IFC file is empty (0 bytes): {file_path}")

        # Validate file extension
        if path.suffix.lower() not in self.VALID_EXTENSIONS:
            raise ValueError(
                f"Invalid file extension '{path.suffix}'. "
                f"Supported extensions: {', '.join(self.VALID_EXTENSIONS)}"
            )

        # Check memory constraint before loading
        self._check_memory_constraint(file_path)

        # Close any previously loaded file
        if self.is_loaded:
            self.close()

        # Track memory usage before loading
        memory_before = self._get_memory_rss()

        # Load the IFC file using IfcOpenShell
        try:
            self._ifc_file = ifcopenshell.open(str(path))
        except MemoryError as e:
            raise MemoryError(
                f"Insufficient memory to load IFC file: {file_path}"
            ) from e
        except ifcopenshell.SchemaError as e:
            # Schema-related parsing errors (invalid schema, missing definitions)
            raise ValueError(
                f"IFC schema error in '{file_path}': {e}. "
                "The file may use an unsupported or malformed schema definition."
            ) from e
        except ifcopenshell.Error as e:
            # IfcOpenShell-specific parsing errors
            error_msg = str(e)
            raise ValueError(self._format_parse_error(file_path, error_msg)) from e
        except RuntimeError as e:
            # Runtime errors during parsing (often from C++ layer)
            raise ValueError(
                f"Failed to parse IFC file '{file_path}': {e}. "
                "The file may be corrupt or contain invalid STEP syntax."
            ) from e
        except Exception as e:
            # Catch-all for unexpected errors
            raise ValueError(
                f"Unexpected error parsing IFC file '{file_path}': {type(e).__name__}: {e}"
            ) from e

        # Track memory usage after loading
        memory_after = self._get_memory_rss()

        # Store memory statistics
        self._memory_stats = MemoryStats(
            memory_before=memory_before,
            memory_after=memory_after,
            file_size=file_size,
        )

        # Store file path and detect schema
        self._file_path = path
        self._schema = self._ifc_file.schema

        # Validate schema is supported
        if self._schema not in self.SUPPORTED_SCHEMAS:
            schema = self._schema
            self.close()
            raise ValueError(
                f"Unsupported IFC schema '{schema}'. "
                f"Supported schemas: {', '.join(self.SUPPORTED_SCHEMAS)}"
            )

    def close(self) -> None:
        """
        Close the currently loaded IFC file and free resources.

        This method should be called when done with the file to
        release memory. It's automatically called when using
        the context manager pattern.

        Note:
            Memory stats are preserved after close() to allow
            post-analysis of memory usage. They are only reset
            when a new file is loaded.
        """
        self._ifc_file = None
        self._file_path = None
        self._schema = None
        # Note: memory_stats intentionally preserved for analysis

    def get_entities_by_type(self, entity_type: str) -> list[Any]:
        """
        Get all entities of a specific type from the loaded IFC file.

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
        """Enter the context manager.

        Enables usage with the 'with' statement for automatic resource
        cleanup when the block exits.

        Returns:
            The IFCParser instance for use within the context block.

        Example:
            >>> with IFCParser() as parser:
            ...     parser.load('model.ifc')
            ...     entities = parser.get_entities_by_type('IfcWall')
            # File automatically closed when exiting the block
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager and close the file.

        Called automatically when exiting a 'with' block. Ensures
        the IFC file is properly closed and resources are released,
        even if an exception occurred within the block.

        Args:
            exc_type: The exception type if an exception was raised, else None.
            exc_val: The exception value if an exception was raised, else None.
            exc_tb: The traceback if an exception was raised, else None.

        Returns:
            None. Exceptions are not suppressed.
        """
        self.close()

    def __repr__(self) -> str:
        """Return a string representation of the parser.

        Provides a human-readable representation showing the current
        state of the parser, including file path and schema if loaded.

        Returns:
            String in format "IFCParser(file='path', schema='IFC4')"
            if loaded, or "IFCParser(not loaded)" if no file is loaded.
        """
        if self.is_loaded:
            return f"IFCParser(file='{self._file_path}', schema='{self._schema}')"
        return "IFCParser(not loaded)"
