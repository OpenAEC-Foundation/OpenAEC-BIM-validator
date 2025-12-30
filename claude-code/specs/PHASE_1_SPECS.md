# Fase 1: Engine + CLI - Specs

## Overzicht

**Duur:** 1 week  
**Doel:** Standalone validatie-engine met CLI  
**Exit criteria:** `ifc-validate model.ifc --ids rules.ids` werkt

---

## Spec 1.1: Project Setup

### Taken
1. Initialiseer Python project met pyproject.toml
2. Setup src/ifc_validator package structuur
3. Configureer Black, Ruff, MyPy
4. Setup pytest met coverage
5. Maak initial README

### Structuur

```
ifc-validator/
├── src/
│   └── ifc_validator/
│       ├── __init__.py
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── validator.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── results.py
│       └── cli.py
├── tests/
│   ├── fixtures/
│   │   ├── minimal.ifc
│   │   └── NL_BIM_Basis_ILS.ids
│   ├── test_parser.py
│   └── test_validator.py
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

### pyproject.toml

```toml
[project]
name = "ifc-validator"
version = "0.1.0"
description = "IFC validation against IDS specifications"
requires-python = ">=3.11"
dependencies = [
    "ifcopenshell>=0.7.0",
    "pydantic>=2.0",
    "typer>=0.9.0",
    "rich>=13.0",
]

[project.scripts]
ifc-validate = "ifc_validator.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=src/ifc_validator"
```

### Acceptatiecriteria
- [ ] `pip install -e .` werkt
- [ ] `ifc-validate --help` toont help
- [ ] `pytest` draait zonder errors
- [ ] MyPy vindt geen type errors

---

## Spec 1.2: IFC Parser Module

### Doel
Wrapper rond IfcOpenShell voor gestructureerde data extractie.

### Code

```python
# src/ifc_validator/engine/parser.py
import ifcopenshell
from pathlib import Path
from typing import Iterator
from ..models.results import IfcElement

class IfcParser:
    def __init__(self, file_path: Path | str):
        self.model = ifcopenshell.open(str(file_path))
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "IfcParser":
        # Create temp file, parse, return
        ...
    
    def get_elements(self, ifc_class: str | None = None) -> Iterator[IfcElement]:
        """Yield all elements, optionally filtered by class."""
        ...
    
    def get_element_by_guid(self, guid: str) -> IfcElement | None:
        """Get single element by GlobalId."""
        ...
    
    @property
    def schema(self) -> str:
        """Return IFC schema (IFC2X3, IFC4, etc.)"""
        return self.model.schema
```

### Acceptatiecriteria
- [ ] Parse IFC2X3 file
- [ ] Parse IFC4 file
- [ ] Extract elements by class
- [ ] Get element properties
- [ ] Handle corrupt files gracefully

---

## Spec 1.3: IDS Validator Module

### Doel
Wrapper rond ifctester voor gestructureerde validatie.

### Code

```python
# src/ifc_validator/engine/validator.py
from ifctester import ids
from pathlib import Path
from ..models.results import ValidationResult, SpecificationResult

class IdsValidator:
    def __init__(self, ids_path: Path | str):
        self.ids_file = ids.open(str(ids_path))
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "IdsValidator":
        ...
    
    def validate(self, parser: IfcParser) -> ValidationResult:
        """Run validation and return structured results."""
        self.ids_file.validate(parser.model)
        
        specs = []
        for spec in self.ids_file.specifications:
            specs.append(SpecificationResult(
                name=spec.name,
                description=spec.description,
                status="pass" if not spec.failed_elements else "fail",
                passed_count=len(spec.applicable_entities) - len(spec.failed_elements),
                failed_count=len(spec.failed_elements),
                failed_elements=[...],
            ))
        
        return ValidationResult(specifications=specs, ...)
    
    def get_specifications(self) -> list[str]:
        """Return list of specification names."""
        return [s.name for s in self.ids_file.specifications]
```

### Acceptatiecriteria
- [ ] Load IDS file
- [ ] Run validation against IFC
- [ ] Return structured results
- [ ] Include failure reasons
- [ ] Support multiple IDS files

---

## Spec 1.4: Result Models

### Doel
Pydantic models voor alle data structuren.

### Code

```python
# src/ifc_validator/models/results.py
from pydantic import BaseModel
from datetime import datetime
from typing import Literal

class IfcElement(BaseModel):
    guid: str
    ifc_class: str
    name: str | None
    type_name: str | None

class FailedElement(BaseModel):
    element: IfcElement
    reason: str
    requirement: str

class SpecificationResult(BaseModel):
    name: str
    identifier: str | None
    description: str | None
    status: Literal["pass", "fail", "warning"]
    passed_count: int
    failed_count: int
    failed_elements: list[FailedElement]

class ValidationSummary(BaseModel):
    total_specs: int
    passed: int
    failed: int
    warnings: int

class ValidationResult(BaseModel):
    id: str
    timestamp: datetime
    ifc_filename: str
    ids_filename: str
    ifc_schema: str
    status: Literal["completed", "failed"]
    summary: ValidationSummary
    specifications: list[SpecificationResult]
```

### Acceptatiecriteria
- [ ] All models serialize to JSON
- [ ] All models validate input
- [ ] Models are documented

---

## Spec 1.5: CLI Tool

### Doel
Command line interface met Typer.

### Code

```python
# src/ifc_validator/cli.py
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from .engine import IfcParser, IdsValidator

app = typer.Typer()
console = Console()

@app.command()
def validate(
    ifc_file: Path = typer.Argument(..., help="Path to IFC file"),
    ids_file: Path = typer.Option(..., "--ids", "-i", help="Path to IDS file"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Validate IFC file against IDS specification."""
    parser = IfcParser(ifc_file)
    validator = IdsValidator(ids_file)
    result = validator.validate(parser)
    
    if format == "json":
        output_json(result, output)
    elif format == "html":
        output_html(result, output)
    else:
        output_table(result)

if __name__ == "__main__":
    app()
```

### Usage

```bash
# Basic
ifc-validate model.ifc --ids rules.ids

# JSON output
ifc-validate model.ifc --ids rules.ids -f json

# Save to file
ifc-validate model.ifc --ids rules.ids -o report.json

# Verbose
ifc-validate model.ifc --ids rules.ids -v
```

### Acceptatiecriteria
- [ ] --help shows usage
- [ ] Validates and shows results
- [ ] JSON output works
- [ ] HTML output works
- [ ] Exit code 0 on pass, 1 on fail

---

## Spec 1.6: Unit Tests

### Fixtures

```
tests/
├── fixtures/
│   ├── minimal.ifc          # Minimal valid IFC
│   ├── sample_building.ifc  # Realistic building
│   ├── invalid.ifc          # Corrupt file
│   ├── simple.ids           # 1 specification
│   └── NL_BIM_Basis_ILS.ids # Complete IDS
├── test_parser.py
├── test_validator.py
├── test_models.py
└── test_cli.py
```

### Test Cases

```python
# tests/test_validator.py
import pytest
from ifc_validator.engine import IdsValidator, IfcParser

class TestIdsValidator:
    def test_load_valid_ids(self, sample_ids_path):
        validator = IdsValidator(sample_ids_path)
        assert len(validator.get_specifications()) > 0
    
    def test_validate_passing_model(self, passing_ifc, sample_ids):
        parser = IfcParser(passing_ifc)
        validator = IdsValidator(sample_ids)
        result = validator.validate(parser)
        assert result.summary.failed == 0
    
    def test_validate_failing_model(self, failing_ifc, sample_ids):
        parser = IfcParser(failing_ifc)
        validator = IdsValidator(sample_ids)
        result = validator.validate(parser)
        assert result.summary.failed > 0
```

### Acceptatiecriteria
- [ ] 80%+ coverage op engine
- [ ] All edge cases tested
- [ ] Tests run in CI
