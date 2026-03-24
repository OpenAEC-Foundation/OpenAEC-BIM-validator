# IFC Web Viewer + IDS Checker + BCF Export

## Project Overview

**Name:** IFC Web Viewer  
**Type:** Open Source Web Application  
**Owner:** 3BM Bouwkunde  
**Business Model:** Open source tool → community building → consultancy/implementation services

## Target Audience

- BIM Coordinators validating IFC deliverables
- Project Managers checking model compliance
- Quality Assurance teams
- Architects and Engineers verifying exports
- Anyone needing quick IFC validation without heavy software

## Core Value Proposition

A lightweight, browser-based tool that allows users to:
1. Upload and view IFC files in 3D
2. Validate against IDS (Information Delivery Specification) rules
3. Export validation issues as BCF for issue tracking

## Tech Stack

### Backend
- **Python 3.11+**
- **IfcOpenShell** - IFC parsing and geometry processing
- **ifctester** - IDS validation engine
- **FastAPI** - REST API framework
- **Redis** - Background job queue

### Frontend
- **That Open Engine** - WebGL IFC viewer
- **React + TypeScript** - UI framework
- **TailwindCSS** - Styling (3BM brand colors)

### Infrastructure
- **Development:** Hetzner CPX21 (4GB RAM, €6/month)
- **Production:** Hetzner AX102 (128GB RAM, €87/month)
- **Docker Compose** - Container orchestration
- **nginx** - Reverse proxy with SSL

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
├─────────────────────────────────────────────────────────────────┤
│  React UI          │  That Open Engine  │  Results Panel        │
│  - Upload form     │  - 3D viewport     │  - Spec list          │
│  - IDS selector    │  - Navigation      │  - Failed items       │
│  - Settings        │  - Selection       │  - BCF platform push  │
└────────┬───────────┴────────┬──────────┴────────┬───────────────┘
         │                    │                    │
         ▼                    │                    ▼
┌─────────────────────┐       │        ┌──────────────────────────┐
│  FastAPI Backend     │       │        │  OpenAEC BCF Platform    │
│  - IFC parsing       │       │        │  /bcf/2.1/projects/...   │
│  - IDS validation    │       │        │  /bcf/2.1/.../topics/... │
│  - Results JSON      │       │        │  (Rust/Axum + PostgreSQL)│
└──────────────────────┘       │        └────────────┬─────────────┘
                               │                     │
                               │                     ▼
                               │            ┌─────────────────────┐
                               │            │  Revit BCF Plugin    │
                               │            │  (download issues)   │
                               │            └─────────────────────┘
                               │
                               ▼
                      ┌─────────────────────┐
                      │  Tauri Desktop App   │
                      │  (zelfde TS code)    │
                      └─────────────────────┘
```

## Key Features

### Phase 1: Core Validation (MVP)
- [x] IFC file upload
- [x] IDS file upload (or select from templates)
- [x] Run validation
- [x] Show pass/fail per specification
- [x] List failed elements with reasons
- [x] CLI tool for batch processing

### Phase 2: Web Interface
- [ ] Simple upload form
- [ ] Results visualization
- [ ] Docker deployment

### Phase 3: 3D Viewer Integration
- [ ] That Open Engine viewport
- [ ] Click-to-select failed elements
- [ ] Highlight failed elements in red
- [ ] Camera fly-to on element click

### Phase 4: BCF Platform Integratie
- [ ] TypeScript BCF Platform client (praat met openaec-bcf-platform API)
- [ ] Validation results → BCF topics mapper
- [ ] Push naar platform per project (met API key auth)
- [ ] Platform UI: project selector, push flow, status
- [ ] BCF ZIP download als lokale fallback (JSZip in browser)
- [ ] Compatibel met Revit BCF plugin download

### Phase 5: Polish & Launch
- [ ] 3BM branding (Magic Violet, Verdigris)
- [ ] Landing page
- [ ] Documentation
- [ ] Production deployment

## Data Models

### ValidationResult
```python
class ValidationResult(BaseModel):
    id: str  # UUID
    status: Literal["pending", "completed", "failed"]
    ifc_filename: str
    ids_filename: str
    timestamp: datetime
    specifications: list[SpecificationResult]
    summary: ValidationSummary

class ValidationSummary(BaseModel):
    total_specs: int
    passed: int
    failed: int
    warnings: int
```

## CLI Interface

```bash
# Basic usage
ifc-validate model.ifc --ids specs.ids

# Output formats
ifc-validate model.ifc --ids specs.ids --format json
ifc-validate model.ifc --ids specs.ids --format html
ifc-validate model.ifc --ids specs.ids --format markdown

# Multiple IDS files
ifc-validate model.ifc --ids *.ids

# Output to file
ifc-validate model.ifc --ids specs.ids -o report.json

# Verbose mode
ifc-validate model.ifc --ids specs.ids -v
```

## Infrastructure

### Development
- Local Docker Compose
- Hot reload for fast iteration

### Production
- **Server:** Hetzner AX102 (128GB RAM, €87/month)
- **Reverse Proxy:** nginx with SSL (Let's Encrypt)
- **Queue:** Redis for async jobs
- **Monitoring:** Sentry + Uptime Kuma

### Capacity
- 5-10 concurrent validations of 500MB models
- Cleanup uploads after 24 hours

## IDS Reference

The project includes:
- **NL_BIM Basis ILS** - Dutch standard for BIM information delivery
- **RVB BIM Norm v1.1** - Rijksvastgoedbedrijf requirements

## Development Guidelines

### Code Style
- Python: Black, Ruff, MyPy strict
- TypeScript: ESLint, Prettier
- Commits: Conventional Commits

### Testing
- Minimum 80% coverage on engine
- Integration tests for API endpoints
- E2E tests for critical flows

### Documentation
- Docstrings in Google style
- README with quickstart
- OpenAPI spec generated from code

## Links

- [IfcOpenShell](https://ifcopenshell.org/)
- [ifctester](https://docs.ifcopenshell.org/ifctester.html)
- [That Open Engine](https://thatopen.com/)
- [IDS Specification](https://technical.buildingsmart.org/projects/information-delivery-specification-ids/)
- [BCF Specification](https://technical.buildingsmart.org/standards/bcf/)
