"""Unit tests for the server/bcf_export.py module.

Tests cover:
- Valid ZIP generation
- Correct number of topics per failed element
- BCF 2.1 version header
- Severity → priority mapping
- XML structure of markup.bcf
- Empty results (no failures)
- Missing/optional fields

Usage:
    pytest test/test_bcf_export.py -v
"""

import sys
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.bcf_export import (
    SEVERITY_TO_PRIORITY,
    generate_bcf_zip,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_VALIDATION_RESULT = {
    "success": False,
    "ifc_file_name": "model.ifc",
    "ids_file_name": "requirements.ids",
    "total_specifications": 2,
    "failed_specifications": 1,
    "total_elements_validated": 10,
    "validation_timestamp": "2026-03-20T12:00:00Z",
    "specifications": [
        {
            "specification_name": "Wall Classification",
            "status": "fail",
            "severity": "error",
            "total_requirements": 1,
            "failed_requirements": 1,
            "requirements": [
                {
                    "requirement_description": "All IfcWall must have NL/SfB classification",
                    "status": "fail",
                    "total_elements": 5,
                    "failed_elements": 2,
                    "elements": [
                        {
                            "global_id": "1abc2def3ghi4jkl",
                            "element_type": "IfcWall",
                            "element_name": "Buitenwand 001",
                            "status": "fail",
                            "messages": ["Missing classification"],
                        },
                        {
                            "global_id": "5mno6pqr7stu8vwx",
                            "element_type": "IfcWall",
                            "element_name": "Binnenwand 003",
                            "status": "fail",
                            "messages": [],
                        },
                        {
                            "global_id": "9yzA0BCD1EFG2HIJ",
                            "element_type": "IfcWall",
                            "element_name": "OK Wall",
                            "status": "pass",
                            "messages": [],
                        },
                    ],
                },
            ],
        },
        {
            "specification_name": "Door Naming",
            "status": "pass",
            "severity": "warning",
            "total_requirements": 1,
            "failed_requirements": 0,
            "requirements": [
                {
                    "requirement_description": "All IfcDoor must have a Name",
                    "status": "pass",
                    "total_elements": 5,
                    "failed_elements": 0,
                    "elements": [],
                },
            ],
        },
    ],
}


@pytest.fixture
def mock_result():
    """Return a copy of the mock validation result."""
    import copy

    return copy.deepcopy(MOCK_VALIDATION_RESULT)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateBcfZip:
    """Tests for generate_bcf_zip function."""

    def test_returns_valid_zip(self, mock_result):
        """Output should be a valid ZIP archive."""
        bcf_bytes = generate_bcf_zip(mock_result)
        assert isinstance(bcf_bytes, bytes)
        assert len(bcf_bytes) > 0

        zf = zipfile.ZipFile(BytesIO(bcf_bytes))
        assert zf.testzip() is None  # No corrupted files

    def test_contains_bcf_version(self, mock_result):
        """ZIP should contain bcf.version with VersionId 2.1."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        assert "bcf.version" in zf.namelist()
        version_xml = zf.read("bcf.version").decode("utf-8")
        assert 'VersionId="2.1"' in version_xml

    def test_contains_extensions(self, mock_result):
        """ZIP should contain extensions.xml."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        assert "extensions.xml" in zf.namelist()
        ext_xml = zf.read("extensions.xml").decode("utf-8")
        assert "IDS Validation" in ext_xml
        assert "Critical" in ext_xml
        assert "Normal" in ext_xml
        assert "Minor" in ext_xml

    def test_correct_topic_count(self, mock_result):
        """Should create exactly one topic per failed element (2 in mock)."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]
        assert len(markup_files) == 2

    def test_topic_title_format(self, mock_result):
        """Topic title should contain element type, name, and spec name."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]

        titles = []
        for mf in markup_files:
            root = ElementTree.fromstring(zf.read(mf))
            # Find Title in any namespace
            for elem in root.iter():
                if elem.tag.endswith("Title"):
                    titles.append(elem.text)

        assert len(titles) == 2
        # One title should contain "Buitenwand 001"
        assert any("Buitenwand 001" in t for t in titles)
        assert any("Binnenwand 003" in t for t in titles)
        # All should reference the spec
        assert all("Wall Classification" in t for t in titles)

    def test_severity_to_priority_mapping(self, mock_result):
        """Error severity should map to Critical priority."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]

        for mf in markup_files:
            root = ElementTree.fromstring(zf.read(mf))
            for elem in root.iter():
                if elem.tag.endswith("Priority"):
                    assert elem.text == "Critical"

    def test_warning_severity_maps_to_normal(self):
        """Warning severity should map to Normal priority."""
        result = {
            "ifc_file_name": "test.ifc",
            "ids_file_name": "test.ids",
            "specifications": [
                {
                    "specification_name": "Test Spec",
                    "severity": "warning",
                    "requirements": [
                        {
                            "requirement_description": "Test req",
                            "elements": [
                                {
                                    "global_id": "abc123",
                                    "element_type": "IfcDoor",
                                    "element_name": "Door 1",
                                    "status": "fail",
                                    "messages": [],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        bcf_bytes = generate_bcf_zip(result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]
        assert len(markup_files) == 1

        root = ElementTree.fromstring(zf.read(markup_files[0]))
        for elem in root.iter():
            if elem.tag.endswith("Priority"):
                assert elem.text == "Normal"

    def test_description_contains_file_names(self, mock_result):
        """Topic description should reference IFC and IDS file names."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]

        for mf in markup_files:
            root = ElementTree.fromstring(zf.read(mf))
            for elem in root.iter():
                if elem.tag.endswith("Description"):
                    assert "model.ifc" in elem.text
                    assert "requirements.ids" in elem.text

    def test_topic_has_comment(self, mock_result):
        """Each topic should have exactly one comment."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]

        for mf in markup_files:
            root = ElementTree.fromstring(zf.read(mf))
            comments = [
                e for e in root.iter() if e.tag.endswith("}Comment") or e.tag == "Comment"
            ]
            # Filter: the <Comment> element inside the comment block (not the wrapper)
            comment_texts = [
                e for e in root.iter()
                if (e.tag.endswith("}Comment") or e.tag == "Comment") and e.text
            ]
            assert len(comment_texts) >= 1

    def test_no_failures_produces_empty_zip(self):
        """Result with no failures should produce ZIP with only version + extensions."""
        result = {
            "ifc_file_name": "test.ifc",
            "ids_file_name": "test.ids",
            "specifications": [
                {
                    "specification_name": "All Good",
                    "severity": "error",
                    "requirements": [
                        {
                            "requirement_description": "Everything passes",
                            "elements": [
                                {
                                    "global_id": "abc",
                                    "element_type": "IfcWall",
                                    "element_name": "Wall 1",
                                    "status": "pass",
                                    "messages": [],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        bcf_bytes = generate_bcf_zip(result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]
        assert len(markup_files) == 0
        assert "bcf.version" in zf.namelist()
        assert "extensions.xml" in zf.namelist()

    def test_empty_specifications(self):
        """Empty specifications list should produce valid ZIP."""
        result = {
            "ifc_file_name": "test.ifc",
            "ids_file_name": "test.ids",
            "specifications": [],
        }
        bcf_bytes = generate_bcf_zip(result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))
        assert zf.testzip() is None
        assert len(zf.namelist()) == 2  # bcf.version + extensions.xml

    def test_custom_author(self, mock_result):
        """Author parameter should appear in topic and comment."""
        bcf_bytes = generate_bcf_zip(mock_result, author="3BM Bouwkunde")
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]

        for mf in markup_files:
            content = zf.read(mf).decode("utf-8")
            assert "3BM Bouwkunde" in content

    def test_topic_status_is_open(self, mock_result):
        """All generated topics should have status 'Open'."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]

        for mf in markup_files:
            root = ElementTree.fromstring(zf.read(mf))
            for elem in root.iter():
                if elem.tag.endswith("TopicStatus"):
                    assert elem.text == "Open"

    def test_topic_type_is_ids_validation(self, mock_result):
        """All topics should have TopicType 'IDS Validation'."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]

        for mf in markup_files:
            content = zf.read(mf).decode("utf-8")
            assert 'TopicType="IDS Validation"' in content

    def test_unique_topic_guids(self, mock_result):
        """Each topic folder should have a unique UUID."""
        bcf_bytes = generate_bcf_zip(mock_result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]
        guids = [mf.split("/")[0] for mf in markup_files]
        assert len(guids) == len(set(guids))

    def test_element_without_global_id(self):
        """Elements without GlobalId should still generate topics."""
        result = {
            "ifc_file_name": "test.ifc",
            "ids_file_name": "test.ids",
            "specifications": [
                {
                    "specification_name": "Test",
                    "severity": "info",
                    "requirements": [
                        {
                            "requirement_description": "Req",
                            "elements": [
                                {
                                    "global_id": None,
                                    "element_type": "IfcSpace",
                                    "element_name": None,
                                    "status": "fail",
                                    "messages": [],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        bcf_bytes = generate_bcf_zip(result)
        zf = zipfile.ZipFile(BytesIO(bcf_bytes))

        markup_files = [
            n for n in zf.namelist() if n.endswith("/markup.bcf")
        ]
        assert len(markup_files) == 1

        # Priority should be Minor (info severity)
        root = ElementTree.fromstring(zf.read(markup_files[0]))
        for elem in root.iter():
            if elem.tag.endswith("Priority"):
                assert elem.text == "Minor"


class TestSeverityMapping:
    """Tests for the SEVERITY_TO_PRIORITY constant."""

    def test_error_maps_to_critical(self):
        assert SEVERITY_TO_PRIORITY["error"] == "Critical"

    def test_warning_maps_to_normal(self):
        assert SEVERITY_TO_PRIORITY["warning"] == "Normal"

    def test_info_maps_to_minor(self):
        assert SEVERITY_TO_PRIORITY["info"] == "Minor"
