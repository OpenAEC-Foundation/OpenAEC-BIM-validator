# Fase 1: Engine + CLI

## Doel
Standalone validatie-engine met command-line interface.

## Specs

### Spec 1.1 - Project Setup
- Initialiseer Python project met pyproject.toml
- Configureer dependencies: ifcopenshell, ifctester, pydantic, typer
- Setup development tools: black, ruff, mypy, pytest
- Configureer pre-commit hooks
- Maak basis mappenstructuur:
  ```
  src/
    ifc_validator/
      __init__.py
      engine/
      cli.py
  tests/
  ```

### Spec 1.2 - IFC Parser Module
- `engine/ifc_parser.py`
- Functie om IFC file te laden met IfcOpenShell
- Support voor IFC2X3 en IFC4
- Memory-efficient loading voor grote bestanden
- Error handling voor corrupte/ongeldige files

### Spec 1.3 - IDS Validator Module
- `engine/ids_validator.py`
- Wrapper rond ifctester
- Load IDS specificatie
- Run validatie tegen IFC model
- Verzamel resultaten in gestructureerd formaat

### Spec 1.4 - Result Models
- `engine/models.py`
- Pydantic models voor:
  - `ValidationResult` - Overall resultaat
  - `SpecificationResult` - Per IDS specification
  - `RequirementResult` - Per requirement
  - `ElementResult` - Per gefaald element
- Serialization naar JSON

### Spec 1.5 - CLI Tool
- `cli.py` met Typer
- Commands:
  - `validate` - Hoofdcommando voor validatie
  - `info` - Toon IFC bestand info
  - `list-specs` - Toon IDS specificaties
- Options:
  - `--ids` - Pad naar IDS bestand
  - `--output` - Output formaat (json/html/console)
  - `--verbose` - Uitgebreide output
- Exit codes voor CI/CD integratie

### Spec 1.6 - Unit Tests
- Tests voor elke module
- Test fixtures met kleine IFC/IDS bestanden
- Mocking van IfcOpenShell waar nodig
- Coverage configuratie (doel: 80%+)

## Exit Criteria
- [ ] `pip install ifc-validator` werkt
- [ ] `ifc-validate model.ifc --ids rules.ids` output JSON/HTML
- [ ] 80%+ test coverage
- [ ] Documentatie in README

## API Signatures

```python
# engine/ifc_parser.py
def load_ifc(file_path: Path) -> ifcopenshell.file:
    """Load IFC file with error handling."""

def get_ifc_info(ifc_file: ifcopenshell.file) -> IFCInfo:
    """Extract metadata from IFC file."""

# engine/ids_validator.py
def load_ids(file_path: Path) -> ids.Ids:
    """Load IDS specification."""

def validate(
    ifc_file: ifcopenshell.file,
    ids_spec: ids.Ids
) -> ValidationResult:
    """Run validation and return structured results."""

# engine/models.py
class ValidationResult(BaseModel):
    file_name: str
    ids_name: str
    timestamp: datetime
    passed: bool
    total_specs: int
    passed_specs: int
    failed_specs: int
    specifications: list[SpecificationResult]
```

## Dependencies
```toml
[project]
dependencies = [
    "ifcopenshell>=0.7.0",
    "ifctester>=0.7.0",
    "pydantic>=2.0",
    "typer>=0.9.0",
    "rich>=13.0",
]
```
