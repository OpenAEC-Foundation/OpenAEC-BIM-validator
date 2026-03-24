# Architecture Decision Records

## ADR-001: Hybrid Architecture (CLI + Web)

**Status:** Accepted  
**Date:** 2025-01-01

### Context
We need both command-line and web interfaces for IFC validation.

### Decision
Build a shared validation engine that both CLI and web interfaces use.

### Consequences
- Engine is a standalone Python package
- CLI wraps engine with argparse
- Web API wraps engine with FastAPI
- Same validation logic everywhere
- Testing focused on engine, interfaces are thin wrappers

---

## ADR-002: IfcOpenShell + ifctester for Validation

**Status:** Accepted  
**Date:** 2025-01-01

### Context
Need to parse IFC files and validate against IDS specifications.

### Decision
Use IfcOpenShell for IFC parsing and ifctester for IDS validation.

### Consequences
- Python backend required
- Mature, well-tested libraries
- Active community support
- IDS 1.0 standard supported

---

## ADR-003: That Open Engine for 3D Viewing

**Status:** Accepted  
**Date:** 2025-01-01

### Context
Need to display IFC models in browser with selection capabilities.

### Decision
Use That Open Engine (formerly IFC.js) for WebGL rendering.

### Consequences
- Client-side rendering (less server load)
- Modern web stack (TypeScript)
- Active development
- Good documentation

---

## ADR-004: Viewer Approach - Deferred Decision

**Status:** Pending Research  
**Date:** 2025-01-01

### Context
Two approaches for getting IFC into browser:
1. **Client-side:** That Open Engine loads IFC directly
2. **Server-side:** IfcConvert creates glTF, browser loads glTF

### Decision
Research both in Phase 0, decide based on:
- Performance with 100MB, 500MB, 1GB files
- Server resource usage
- Feature support (selection, properties)
- SVG floor plan generation (bonus for server-side)

### Consequences
- Phase 0 extended with comparison task
- May affect infrastructure requirements
- Hybrid approach possible (small files client, large server)

---

## ADR-005: Hetzner for Hosting

**Status:** Accepted  
**Date:** 2025-01-01

### Context
Need affordable, high-memory VPS for IFC processing.

### Decision
- **Development:** Hetzner CPX21 (4GB RAM, €6/month)
- **Production:** Hetzner AX102 (128GB RAM, €87/month)

### Consequences
- Excellent price/performance
- EU data center (GDPR compliant)
- 128GB handles 10+ concurrent 1GB models
- Good network (1Gbps+)

---

## ADR-006: BCF 2.1 via OpenAEC BCF Platform

**Status:** Accepted (updated 2026-03-24)
**Date:** 2025-01-01

### Context
Validation failures need to be shareable with authoring tools.
We have built a separate BCF Platform (openaec-bcf-platform) with full BCF 2.1 API.

### Decision
Push validation results as BCF topics to OpenAEC BCF Platform via REST API.
Additionally support local BCF ZIP download as fallback.

### Consequences
- Issues stored centrally per project on platform
- Status tracking, overzichten, en dashboards op platform
- Revit users can download via BCF plugin
- API key auth per project
- Platform must be reachable from validator frontend
- No Python BCF generator needed — all in TypeScript

---

## ADR-008: Geen Python voor BCF — TypeScript nu, Rust crate later

**Status:** Accepted
**Date:** 2026-03-24

### Context
BCF integratie moet herbruikbaar zijn buiten de web-app:
- Tauri desktop app
- Solibri plugin (BCF upload)
- Revit plugin (BCF download/upload)
- CLI tools

Python is niet herbruikbaar in deze contexten.

### Decision
- **Fase 4 (nu):** Lichtgewicht TypeScript client in validator frontend
- **Later:** Gedeelde Rust `bcf-client` crate die compileert naar native + WASM
- Python backend doet alleen IFC parsing + IDS validatie

### Consequences
- TypeScript client is snel te bouwen, voldoende voor web-app
- Later vervangbaar door WASM-compiled Rust crate zonder API-wijzigingen
- Rust crate herbruikbaar in Tauri, Solibri plugin, Revit plugin
- Geen Python BCF dependencies
- Frontend praat direct met BCF Platform API (twee backends)

---

## ADR-007: Docker for Deployment

**Status:** Accepted  
**Date:** 2025-01-01

### Context
Need reproducible deployments across environments.

### Decision
Use Docker Compose for development and production.

### Consequences
- Consistent environments
- Easy scaling
- nginx reverse proxy in container
- Redis for job queue in container
