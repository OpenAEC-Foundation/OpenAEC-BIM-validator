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

### Gedaan in vorige sessie (2026-03-29)
- **Ghost mode bug opgelost:**
  - Fix: vervangen door `FragmentsModel.setOpacity()` / `resetOpacity()` / `setColor()` — fragment-level per-element controle

### Gedaan in deze sessie (2026-03-30)
- **Save / Save As / Open functionaliteit (Fase 7d):**
  - Nieuwe projectIoSlice in Zustand store: tracked save source (local/cloud), dirty state, project naam
  - Ribbon Home tab: nieuwe "Project" groep met Opslaan (Ctrl+S), Opslaan als (Ctrl+Shift+S), Openen (Ctrl+O) knoppen
  - SaveAsDialog: tweestaps modal met keuze lokaal/cloud, lokaal genereert .zip met IFC + validatieresultaten
  - OpenDialog: tweestaps modal met keuze lokaal/cloud, lokaal accepteert .ifc/.ids/.zip bestanden
  - Keyboard shortcuts uitgebreid met Ctrl+S, Ctrl+Shift+S, Ctrl+O
  - Save icon, SaveAs icon, Open icon toegevoegd aan ribbon icon set
  - i18n projectIo namespace aangemaakt (NL + EN) met alle dialoogteksten
  - AppShell geintegreerd met beide dialogen + escape handler
  - Build slaagt (npm run build)

- **Project container model migratie:**
  - nextcloud_client.py: nieuwe constanten (DIR_MODELS, DIR_VALIDATION, MANIFEST_FILENAME)
  - nextcloud_client.py: _tool_path schrijft nu naar validation/ i.p.v. 99_overige_documenten/bim-validator/
  - nextcloud_client.py: list_models() met fallback models/ → 70_BIM/
  - nextcloud_client.py: list_validation_files() met fallback validation/ → 99_overige_documenten/bim-validator/
  - nextcloud_client.py: download_file() met fallback new → legacy
  - nextcloud_client.py: upload_to_validation() — altijd naar validation/
  - nextcloud_client.py: manifest CRUD — read_manifest(), write_manifest(), upsert_manifest_object()
  - volume_reader.py: list_bim_files() met fallback models/ → 70_BIM/
  - volume_reader.py: list_output_files() met fallback validation/ → 99_overige_documenten/bim-validator/
  - volume_reader.py: get_file_path() met automatic legacy fallback
  - volume_reader.py: read_manifest() voor volume mount reads
  - routers/cloud.py: file listing gebruikt list_models/list_validation_files (met fallback)
  - routers/cloud.py: upload gaat naar validation/ directory
  - routers/cloud.py: save endpoint schrijft WefcValidation object naar manifest
  - routers/cloud.py: nieuw GET /api/cloud/projects/{project}/manifest endpoint
  - models/cloud.py: ManifestHeader + ManifestResponse Pydantic models
  - tests: 19 tests voor nextcloud_client (constanten, paths, fallback, manifest CRUD)
  - tests: 7 tests voor cloud endpoints (manifest, category routing, volume mount)
  - Alle 26 tests slagen

### Nog te doen
- NC_SERVICE_PASS_3BM instellen in .env op server → cloud wordt actief
- Cloud status testen na wachtwoord configuratie
- OIDC tenant claim koppelen aan tenant selectie (nu hardcoded default "3bm")
- Frontend: ProjectList component updaten voor manifest-aware weergave
