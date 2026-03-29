# Project Status — 2026-03-29

## Huidige fase: Fase 7 (Hybrid Cloud + Multi-tenant) — deployed

### Wat is af
- Fase 0: Research & validatie
- Fase 1: Engine + CLI
- Fase 2: Web interface (FastAPI + React)
- Fase 3: 3D Viewer koppeling
- Deployment setup (Docker + Hetzner)
- Fase 4: BCF Issue Management — gebouwd + deployed
- Fase 5: Chrome Design System — ribbon, backstage, i18n, theming
- Fase 6: Nextcloud Cloud Storage — WebDAV, save/open dialog
- **Fase 7a: Project Management** — PostgreSQL backend, REST API, frontend UI
- **Fase 7b: Hybrid Nextcloud I/O** — volume mount reads, WebDAV writes, multi-tenant

### Gedaan in vorige sessie (2026-03-28)
- Project management systeem gebouwd (full-stack):
  - Backend: async SQLAlchemy 2.0 + PostgreSQL (SQLite fallback)
  - ORM models: Project + ProjectFile
  - REST API: /api/v2/projects CRUD + file upload/download/delete
  - Frontend: IProjectStorage interface + ServerProjectStorage + LocalProjectStorage
  - .bvp bestandsformaat voor lokale projecten (File System Access API)
  - ProjectList component in Backstage + i18n (NL + EN)
  - AppShell integratie met handleOpenProject
- Hybrid Nextcloud I/O migratie:
  - server/tenant_config.py: multi-tenant config loader (tenants.json)
  - server/volume_reader.py: directe filesystem reads van NC volume mount
  - server/routers/cloud.py: refactored cloud router (was inline in main.py)
  - NextcloudClient: multi-tenant factory (from_tenant) + client registry
  - docker-compose.yml: NC data volume (ro), tenant config mount
  - config/tenants.json: 3BM tenant configuratie
- Ghost mode pogingen (nog niet werkend):
  - Opacity 0.85→0.15: transparantie zelf werkt nu
  - Reset knop werkt
  - Geselecteerd element wordt nog NIET opaque getoond
  - Poging 1: mesh-level material restore → werkt niet (IFC batcht elementen in shared meshes)
  - Poging 2: fragment highlight overlay met opacity 1.0 → werkt ook niet
  - Moet dieper onderzocht worden hoe That Open Engine fragment highlights werken
- Deployed naar Hetzner (commits a2d3b11, 5c8ba74, d12678f, 3674eb5)

### Gedaan in deze sessie (2026-03-29)
- **Ghost mode debug (nog niet opgelost):**
  - Poging 3: `FragmentsModel.setOpacity()` / `resetOpacity()` / `setColor()` → deployed maar werkt niet (niets werd transparant, vermoedelijk incompatibel met tile streaming)
  - Poging 4: material-level ghost + `depthWrite=false` + fragment highlight overlay → deployed maar highlight overlay rendert nog steeds niet opaque over de ghosted materials
  - Huidige deployed state (commit b4ae89a): material-level ghost met depthWrite=false, highlight overlay niet zichtbaar als opaque

### Volgende sessie: ghost mode debug
- Browser console openen en kijken of `fragments.highlight()` errors geeft
- Checken of `guidsToModelIdMap` daadwerkelijk data teruggeeft
- Alternatieve aanpak overwegen (Hider.isolate, kloon geometry, twee render passes)

### Nog te doen
- NC_SERVICE_PASS_3BM instellen in .env op server → cloud wordt actief
- Cloud status testen na wachtwoord configuratie
- OIDC tenant claim koppelen aan tenant selectie (nu hardcoded default "3bm")
