"""Pytest configuration and fixtures for server validation endpoint tests.

This conftest.py provides test fixtures for testing the validation endpoint,
including TestClient, sample IFC/IDS files, and cleanup utilities.
"""

import io
import sys
from pathlib import Path

import pytest

# Add project root and src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Clear any existing ifc_validator paths from sys.path to prevent cross-contamination
sys.path = [p for p in sys.path if "ifc_validator" not in p and "worktrees" not in str(p) or str(PROJECT_ROOT) in str(p)]

# Insert our project's src at the beginning (for ifc_validator module)
src_path = str(PROJECT_ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Insert the project root (for server module)
project_path = str(PROJECT_ROOT)
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from fastapi.testclient import TestClient

from server.main import app, uploaded_files


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_ifc_content():
    """Sample valid IFC file content for testing.

    This is a minimal valid IFC4 file with:
    - Project structure (Project, Site, Building, Storey)
    - One wall element (IfcWallStandardCase) named 'W-001'
    - Proper naming convention that passes the sample IDS spec
    """
    return b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('sample.ifc','2025-01-01T12:00:00',('Test Author'),('Test Organization'),'IfcOpenShell','IfcOpenShell','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPERSON($,$,'Test User',$,$,$,$,$);
#2=IFCORGANIZATION($,'Test Organization',$,$,$);
#3=IFCPERSONANDORGANIZATION(#1,#2,$);
#4=IFCAPPLICATION(#2,'1.0','Test Application','TestApp');
#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,1704067200);
#6=IFCDIRECTION((1.,0.,0.));
#7=IFCDIRECTION((0.,0.,1.));
#8=IFCCARTESIANPOINT((0.,0.,0.));
#9=IFCAXIS2PLACEMENT3D(#8,#7,#6);
#10=IFCDIRECTION((0.,1.,0.));
#11=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#9,#10);
#12=IFCDIMENSIONALEXPONENTS(0,0,0,0,0,0,0);
#13=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#14=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#15=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#16=IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.);
#17=IFCMEASUREWITHUNIT(IFCPLANEANGLEMEASURE(0.017453292519943295),#16);
#18=IFCCONVERSIONBASEDUNIT(#12,.PLANEANGLEUNIT.,'DEGREE',#17);
#19=IFCUNITASSIGNMENT((#13,#14,#15,#18));
#20=IFCPROJECT('2XyZ3W4aa56Bjd9gQc07yA',#5,'Test Project',$,$,$,$,(#11),#19);
#21=IFCSITE('1AbC2D3eF45GhIjKlMnOpQ',#5,'Test Site',$,$,$,$,$,.ELEMENT.,$,$,$,$,$);
#22=IFCBUILDING('3RsT4U5vW67XyZ0AbCdEfG',#5,'Test Building',$,$,$,$,$,.ELEMENT.,$,$,$);
#23=IFCBUILDINGSTOREY('4HiJ5K6lM78NoPqRsTuVwX',#5,'00 Ground Floor',$,$,$,$,$,.ELEMENT.,0.);
#24=IFCRELAGGREGATES('5YzA6B7cD89EfGhIjKlMnO',#5,$,$,#20,(#21));
#25=IFCRELAGGREGATES('6PqR7S8tU90VwXyZaBcDeF',#5,$,$,#21,(#22));
#26=IFCRELAGGREGATES('7GhI8J9kL01MnOpQrStUvW',#5,$,$,#22,(#23));
#27=IFCLOCALPLACEMENT($,#9);
#28=IFCCARTESIANPOINT((0.,0.,0.));
#29=IFCCARTESIANPOINT((5000.,0.,0.));
#30=IFCPOLYLINE((#28,#29));
#31=IFCSHAPEREPRESENTATION(#11,'Axis','Curve2D',(#30));
#32=IFCCARTESIANPOINT((0.,0.,0.));
#33=IFCCARTESIANPOINT((5000.,0.,0.));
#34=IFCCARTESIANPOINT((5000.,200.,0.));
#35=IFCCARTESIANPOINT((0.,200.,0.));
#36=IFCPOLYLINE((#32,#33,#34,#35,#32));
#37=IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,$,#36);
#38=IFCDIRECTION((0.,0.,1.));
#39=IFCEXTRUDEDAREASOLID(#37,#9,#38,3000.);
#40=IFCSHAPEREPRESENTATION(#11,'Body','SweptSolid',(#39));
#41=IFCPRODUCTDEFINITIONSHAPE($,$,(#31,#40));
#42=IFCWALLSTANDARDCASE('8XyZ9A0bC12DeFgHiJkLmN',#5,'W-001','Test Wall',$,#27,#41,$,.NOTDEFINED.);
#43=IFCRELCONTAINEDINSPATIALSTRUCTURE('9OpQ0R1sT23UvWxYzAbCdE',#5,$,$,(#42),#23);
ENDSEC;
END-ISO-10303-21;
"""


@pytest.fixture
def sample_ifc_content_fail():
    """Sample IFC file content that fails validation.

    This IFC file has a wall with an invalid name (doesn't match W-### pattern),
    so it will fail validation against the sample IDS spec.
    """
    return b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('sample-fail.ifc','2025-01-01T12:00:00',('Test Author'),('Test Organization'),'IfcOpenShell','IfcOpenShell','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPERSON($,$,'Test User',$,$,$,$,$);
#2=IFCORGANIZATION($,'Test Organization',$,$,$);
#3=IFCPERSONANDORGANIZATION(#1,#2,$);
#4=IFCAPPLICATION(#2,'1.0','Test Application','TestApp');
#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,1704067200);
#6=IFCDIRECTION((1.,0.,0.));
#7=IFCDIRECTION((0.,0.,1.));
#8=IFCCARTESIANPOINT((0.,0.,0.));
#9=IFCAXIS2PLACEMENT3D(#8,#7,#6);
#10=IFCDIRECTION((0.,1.,0.));
#11=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#9,#10);
#12=IFCDIMENSIONALEXPONENTS(0,0,0,0,0,0,0);
#13=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#14=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#15=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#16=IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.);
#17=IFCMEASUREWITHUNIT(IFCPLANEANGLEMEASURE(0.017453292519943295),#16);
#18=IFCCONVERSIONBASEDUNIT(#12,.PLANEANGLEUNIT.,'DEGREE',#17);
#19=IFCUNITASSIGNMENT((#13,#14,#15,#18));
#20=IFCPROJECT('2XyZ3W4aa56Bjd9gQc07yB',#5,'Test Project',$,$,$,$,(#11),#19);
#21=IFCSITE('1AbC2D3eF45GhIjKlMnOpR',#5,'Test Site',$,$,$,$,$,.ELEMENT.,$,$,$,$,$);
#22=IFCBUILDING('3RsT4U5vW67XyZ0AbCdEfH',#5,'Test Building',$,$,$,$,$,.ELEMENT.,$,$,$);
#23=IFCBUILDINGSTOREY('4HiJ5K6lM78NoPqRsTuVwY',#5,'Ground Floor',$,$,$,$,$,.ELEMENT.,0.);
#24=IFCRELAGGREGATES('5YzA6B7cD89EfGhIjKlMnP',#5,$,$,#20,(#21));
#25=IFCRELAGGREGATES('6PqR7S8tU90VwXyZaBcDeG',#5,$,$,#21,(#22));
#26=IFCRELAGGREGATES('7GhI8J9kL01MnOpQrStUvX',#5,$,$,#22,(#23));
#27=IFCLOCALPLACEMENT($,#9);
#28=IFCCARTESIANPOINT((0.,0.,0.));
#29=IFCCARTESIANPOINT((5000.,0.,0.));
#30=IFCPOLYLINE((#28,#29));
#31=IFCSHAPEREPRESENTATION(#11,'Axis','Curve2D',(#30));
#32=IFCCARTESIANPOINT((0.,0.,0.));
#33=IFCCARTESIANPOINT((5000.,0.,0.));
#34=IFCCARTESIANPOINT((5000.,200.,0.));
#35=IFCCARTESIANPOINT((0.,200.,0.));
#36=IFCPOLYLINE((#32,#33,#34,#35,#32));
#37=IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,$,#36);
#38=IFCDIRECTION((0.,0.,1.));
#39=IFCEXTRUDEDAREASOLID(#37,#9,#38,3000.);
#40=IFCSHAPEREPRESENTATION(#11,'Body','SweptSolid',(#39));
#41=IFCPRODUCTDEFINITIONSHAPE($,$,(#31,#40));
#42=IFCWALLSTANDARDCASE('8XyZ9A0bC12DeFgHiJkLmO',#5,'Bad Wall Name','Test Wall Without Proper Name',$,#27,#41,$,.NOTDEFINED.);
#43=IFCRELCONTAINEDINSPATIALSTRUCTURE('9OpQ0R1sT23UvWxYzAbCdF',#5,$,$,(#42),#23);
ENDSEC;
END-ISO-10303-21;
"""


@pytest.fixture
def sample_ids_content():
    """Sample IDS specification file content for testing.

    This IDS spec requires walls (IfcWallStandardCase) to have names
    matching the pattern 'W-###' (e.g., W-001, W-002).
    """
    return b"""<?xml version="1.0" encoding="utf-8"?>
<ids xmlns:xs="http://www.w3.org/2001/XMLSchema"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://standards.buildingsmart.org/IDS http://standards.buildingsmart.org/IDS/1.0/ids.xsd"
     xmlns="http://standards.buildingsmart.org/IDS">
  <info>
    <title>Test IDS Specification</title>
    <copyright>Test Organization</copyright>
    <version>1.0</version>
    <description>Minimal IDS for endpoint testing</description>
    <author>test@example.com</author>
    <date>2025-01-01</date>
    <purpose>Unit and integration testing of validation endpoint</purpose>
  </info>
  <specifications>
    <specification name="Wall Naming Convention" ifcVersion="IFC2X3 IFC4" identifier="TEST-001" description="Walls must have names starting with W-" instructions="Name walls using pattern: W-[number]">
      <applicability minOccurs="1" maxOccurs="unbounded">
        <entity>
          <name>
            <simpleValue>IFCWALLSTANDARDCASE</simpleValue>
          </name>
        </entity>
      </applicability>
      <requirements>
        <attribute cardinality="required" instructions="Wall name must start with W-">
          <name>
            <simpleValue>Name</simpleValue>
          </name>
          <value>
            <xs:restriction base="xs:string">
              <xs:pattern value="W-\\d{3}.*"/>
            </xs:restriction>
          </value>
        </attribute>
      </requirements>
    </specification>
  </specifications>
</ids>
"""


@pytest.fixture
def sample_ifc_file(sample_ifc_content):
    """Create a file-like object for IFC upload testing."""
    return ("test_model.ifc", io.BytesIO(sample_ifc_content), "application/octet-stream")


@pytest.fixture
def sample_ifc_file_fail(sample_ifc_content_fail):
    """Create a file-like object for IFC upload that will fail validation."""
    return ("test_model_fail.ifc", io.BytesIO(sample_ifc_content_fail), "application/octet-stream")


@pytest.fixture
def sample_ids_file(sample_ids_content):
    """Create a file-like object for IDS upload testing."""
    return ("test_spec.ids", io.BytesIO(sample_ids_content), "application/octet-stream")


@pytest.fixture(autouse=True)
def cleanup_uploaded_files():
    """Clean up uploaded_files tracking dict before and after each test."""
    # Clear before test
    uploaded_files.clear()
    yield
    # Clear after test
    uploaded_files.clear()


# =============================================================================
# File Path Fixtures (for integration tests using real files)
# =============================================================================


@pytest.fixture
def fixtures_dir():
    """Return the path to the test fixtures directory."""
    return PROJECT_ROOT / "test" / "fixtures"


@pytest.fixture
def sample_ifc_path(fixtures_dir):
    """Return path to the sample.ifc fixture file."""
    path = fixtures_dir / "sample.ifc"
    if not path.exists():
        pytest.skip(f"Sample IFC fixture not found: {path}")
    return path


@pytest.fixture
def sample_ids_path(fixtures_dir):
    """Return path to the sample.ids fixture file."""
    path = fixtures_dir / "sample.ids"
    if not path.exists():
        pytest.skip(f"Sample IDS fixture not found: {path}")
    return path


@pytest.fixture
def sample_fail_ifc_path(fixtures_dir):
    """Return path to the sample-fail.ifc fixture file."""
    path = fixtures_dir / "sample-fail.ifc"
    if not path.exists():
        pytest.skip(f"Sample fail IFC fixture not found: {path}")
    return path
