"""Test that the ids_validator module can be imported from server package without errors.

These tests verify the module can be properly imported and used as a package.
This is important for ensuring the module integrates correctly with the FastAPI
server and can be used by other components.

Usage:
    pytest test/test_module_imports.py -v
    python test/test_module_imports.py  # Run as standalone script
"""

import sys
import warnings
from pathlib import Path

import pytest

# Add project root to path for imports (same pattern as test_ids_validator.py)
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestModuleImports:
    """Test suite for verifying module imports work correctly."""

    def test_import_ids_validator_class(self):
        """Test importing IDSValidator class from server package."""
        from server.ids_validator import IDSValidator

        assert IDSValidator is not None
        assert callable(IDSValidator)

    def test_import_validate_function(self):
        """Test importing validate_ifc_against_ids function from server package."""
        from server.ids_validator import validate_ifc_against_ids

        assert validate_ifc_against_ids is not None
        assert callable(validate_ifc_against_ids)

    def test_import_report_to_dict_function(self):
        """Test importing report_to_dict function from server package."""
        from server.ids_validator import report_to_dict

        assert report_to_dict is not None
        assert callable(report_to_dict)

    def test_import_entity_failure_dataclass(self):
        """Test importing EntityFailure dataclass from server package."""
        from server.ids_validator import EntityFailure

        assert EntityFailure is not None
        # Verify it's a dataclass by checking for __dataclass_fields__
        assert hasattr(EntityFailure, "__dataclass_fields__")

    def test_import_specification_result_dataclass(self):
        """Test importing SpecificationResult dataclass from server package."""
        from server.ids_validator import SpecificationResult

        assert SpecificationResult is not None
        assert hasattr(SpecificationResult, "__dataclass_fields__")

    def test_import_validation_report_dataclass(self):
        """Test importing ValidationReport dataclass from server package."""
        from server.ids_validator import ValidationReport

        assert ValidationReport is not None
        assert hasattr(ValidationReport, "__dataclass_fields__")

    def test_import_all_public_exports(self):
        """Test importing all public exports from the module in one statement."""
        from server.ids_validator import (
            EntityFailure,
            IDSValidator,
            SpecificationResult,
            ValidationReport,
            report_to_dict,
            validate_ifc_against_ids,
        )

        # All imports should succeed
        assert IDSValidator is not None
        assert validate_ifc_against_ids is not None
        assert report_to_dict is not None
        assert EntityFailure is not None
        assert SpecificationResult is not None
        assert ValidationReport is not None

    def test_module_has_no_import_warnings(self):
        """Test that importing the module produces no warnings."""
        # Clear any cached imports
        if "server.ids_validator" in sys.modules:
            del sys.modules["server.ids_validator"]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import server.ids_validator  # noqa: F401

            # Filter out any deprecation warnings from third-party libraries
            module_warnings = [
                warning
                for warning in w
                if "ids_validator" in str(warning.filename)
            ]
            assert len(module_warnings) == 0, (
                f"Import produced warnings: {[str(warning.message) for warning in module_warnings]}"
            )

    def test_ids_validator_instantiation(self):
        """Test that IDSValidator can be instantiated without errors."""
        from server.ids_validator import IDSValidator

        validator = IDSValidator()
        assert validator is not None
        assert isinstance(validator, IDSValidator)

    def test_get_capabilities_works_after_import(self):
        """Test that get_capabilities works correctly after import."""
        from server.ids_validator import IDSValidator

        validator = IDSValidator()
        caps = validator.get_capabilities()

        assert isinstance(caps, dict)
        assert "ifcopenshell_version" in caps
        assert "ifctester_version" in caps
        assert "supported_ids_versions" in caps
        assert "validation_available" in caps
        assert caps["validation_available"] is True


# Standalone script execution
if __name__ == "__main__":
    print("=" * 60)
    print("Testing server.ids_validator module imports")
    print("=" * 60)

    test_instance = TestModuleImports()
    tests = [
        ("test_import_ids_validator_class", test_instance.test_import_ids_validator_class),
        ("test_import_validate_function", test_instance.test_import_validate_function),
        ("test_import_report_to_dict_function", test_instance.test_import_report_to_dict_function),
        ("test_import_entity_failure_dataclass", test_instance.test_import_entity_failure_dataclass),
        ("test_import_specification_result_dataclass", test_instance.test_import_specification_result_dataclass),
        ("test_import_validation_report_dataclass", test_instance.test_import_validation_report_dataclass),
        ("test_import_all_public_exports", test_instance.test_import_all_public_exports),
        ("test_module_has_no_import_warnings", test_instance.test_module_has_no_import_warnings),
        ("test_ids_validator_instantiation", test_instance.test_ids_validator_instantiation),
        ("test_get_capabilities_works_after_import", test_instance.test_get_capabilities_works_after_import),
    ]

    passed = 0
    failed = 0
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        try:
            test_func()
            print("OK")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{passed + failed} tests passed")

    if failed == 0:
        print("SUCCESS: All module import tests passed!")
        sys.exit(0)
    else:
        print("FAILURE: Some module import tests failed!")
        sys.exit(1)
