# Project Status — 2026-03-30

## Huidige fase: Fase 7 (Hybrid Cloud + Multi-tenant + Project Container + Save/Open) — in progress

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
- **Fase 7c: Project Container Model** — migratie naar models/validation/ structuur met project.wefc manifest

### Gedaan in sessie 2026-03-28
- Project management systeem gebouwd (full-stack)
- Hybrid Nextcloud I/O migratie (tenant_config, volume_reader, cloud router)
- Ghost mode pogingen (nog niet werkend)
- Deployed naar Hetzner

### Gedaan in sessie 2026-03-29
- Ghost mode debug (poging 3+4, niet opgelost)
- Ghost mode bug opgelost: `FragmentsModel.setOpacity()` / `resetOpacity()` / `setColor()`

### Gedaan in sessie 2026-03-30
- **Save / Save As / Open functionaliteit (Fase 7d):**
  - projectIoSlice, Ribbon knoppen, SaveAsDialog, OpenDialog, keyboard shortcuts, i18n
  - Build slaagt (npm run build)

- **Project container model migratie:**
  - nextcloud_client.py: DIR_MODELS, DIR_VALIDATION, MANIFEST_FILENAME, fallback paden
  - nextcloud_client.py: manifest CRUD — read_manifest(), write_manifest(), upsert_manifest_object()
  - volume_reader.py: list_bim_files(), list_output_files(), get_file_path() met legacy fallback
  - routers/cloud.py: file listing met fallback, upload naar validation/, manifest endpoint
  - models/cloud.py: ManifestHeader + ManifestResponse Pydantic models
  - 26 tests slagen (19 nextcloud_client + 7 cloud endpoints)

### Nog te doen
- NC_SERVICE_PASS_3BM instellen in .env op server → cloud wordt actief
- Cloud status testen na wachtwoord configuratie
- OIDC tenant claim koppelen aan tenant selectie (nu hardcoded default "3bm")
- Frontend: ProjectList component updaten voor manifest-aware weergave
