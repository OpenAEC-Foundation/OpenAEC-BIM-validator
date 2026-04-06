# CLAUDE.md - Project Context for Claude Code

## Project: IFC Web Viewer + IDS Validator

### Quick Summary
Browser-based IFC validation tool using IDS specifications, with 3D viewing and BCF export. Open source by 3BM Bouwkunde.

### Tech Stack
- **Backend:** Python 3.11+, FastAPI, IfcOpenShell, ifctester
- **Frontend:** React, TypeScript, That Open Engine, TailwindCSS
- **Infra:** Docker, nginx, Redis, Hetzner

### Key Files
- `src/ifc_validator/engine/` - Core validation logic
- `src/ifc_validator/cli.py` - Command line interface
- `src/ifc_validator/web/` - FastAPI application
- `frontend/` - React application
- `tests/` - Pytest tests

### Commands
```bash
# Run tests
pytest -v

# Run CLI
python -m ifc_validator.cli model.ifc --ids rules.ids

# Run web server (dev)
uvicorn ifc_validator.web.app:app --reload

# Build frontend
cd frontend && npm run build

# Docker
docker compose up -d
```

### Code Style
- Python: Black, Ruff, MyPy strict
- TypeScript: ESLint, Prettier
- Use Google-style docstrings
- Conventional commits

### Architecture Principles
1. Engine is standalone, interfaces are thin wrappers
2. Pydantic models for all data structures
3. Type hints everywhere
4. Tests before implementation (TDD preferred)

### Current Phase
Check ROADMAP.md for current phase and specs.

### IDS Files
- `fixtures/NL_BIM_Basis_ILS.ids` - Dutch BIM standard
- `fixtures/RVB_BIM_Norm_v1.1.ids` - Rijksvastgoed standard

### 3BM Brand Colors
- Magic Violet: #350E35
- Verdigris: #44B6A8
- Friendly Yellow: #EFBD75
- Warm Magenta: #A01C48
- Flaming Peach: #DB4C40

### Important Notes
- IFC files can be 1GB+, memory management critical
- 10x file size in RAM during processing
- Clean up temp files aggressively
- Support both IFC2X3 and IFC4

---

## Agent Broker
- **project_id:** `bim-validator`
- **display_name:** `BIM Validator`
- **capabilities:** `["ifc-validation", "ids", "bcf-export"]`
- **subscriptions:** `["bim/*", "shared/*"]`

---

## Orchestrator

Bij sessie START → lees:
- `X:\10_3BM_bouwkunde\50_Claude-Code-Projects\lessons_learned_global.md`
- `C:\Users\JochemK\.claude\orchestrator\sessions\bim-validator_latest.md` (indien aanwezig)

Bij sessie EINDE → schrijf update naar:
`C:\Users\JochemK\.claude\orchestrator\sessions\bim-validator_latest.md`

**Registry:** `C:\Users\JochemK\.claude\orchestrator\project-registry.json`
