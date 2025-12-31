# Phase 0 - Research & Validation

This folder contains the research and validation work for the BIM validation tech stack feasibility study.

## Purpose

Pre-implementation validation phase to test technical feasibility before committing to full system development. The phase validates:

1. **IDS Validation** - ifctester library's ability to validate IFC models against the Dutch NL_BIM_Basis_ILS.ids standard
2. **3D Rendering** - That Open Engine's browser-based 3D rendering capabilities
3. **Rendering Comparison** - Client-side versus server-side rendering approaches

## Folder Structure

```
research/
├── README.md                    # This file
├── test_ids_loading.py          # IDS file loading tests
├── test_ifc_loading.py          # IFC file loading tests
├── test_validation.py           # End-to-end validation tests
├── validation_poc.py            # Validation proof-of-concept script
├── test_results.md              # Compiled test results
├── browser_compatibility.md     # Browser compatibility report
├── client_performance.md        # Client-side rendering metrics
├── server_performance.md        # Server-side rendering metrics
├── performance_comparison.md    # Comparative analysis
└── decision.md                  # Go/No-Go decision document
```

## Key Dependencies

- **ifcopenshell** (v0.8.4.post1) - IFC file parsing and manipulation
- **ifctester** (v0.8.4) - IDS validation engine
- **fastapi** - Web API framework for server-side POC
- **python-multipart** - File upload support for FastAPI

## Quick Start

```bash
# Install research dependencies
pip install -r requirements-research.txt

# Run existing tests to verify setup
pytest test/

# Run IDS loading test
python research/test_ids_loading.py

# Run validation POC
python research/validation_poc.py
```

## Test Files

- **IFC Test Model**: `test/2786_CLT_model.ifc`
- **IDS Specification**: `ids-bestanden/NL_BIM_Basis_ILS.ids`

## Related Documentation

- Spec: `.auto-claude/specs/001-phase-0-research-validatie/spec.md`
- Implementation Plan: `.auto-claude/specs/001-phase-0-research-validatie/implementation_plan.json`
