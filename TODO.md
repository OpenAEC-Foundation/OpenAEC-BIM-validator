# TODO

## Bug: Ghost mode — geselecteerd element niet opaque — OPGELOST
- [x] Oorzaak: material-level opacity beïnvloedt alle elementen in shared meshes (IFC batching)
- [x] Fragment highlight overlay werkt niet omdat transparante materials erover heen renderen
- **Geprobeerde fixes die NIET werkten:**
  - Poging 1: mesh-level material restore → werkt niet (shared meshes)
  - Poging 2: fragment highlight overlay (opacity 1.0, RenderedFaces.TWO) → overlay niet zichtbaar
  - Poging 3: FragmentsModel.setOpacity()/resetOpacity()/setColor() → niets transparant (tile streaming?)
  - Poging 4: material ghost + depthWrite=false + highlight overlay → highlight nog steeds niet opaque
- [x] **Oplossing (split-out patroon):** de geometrie van het geselecteerde element
  wordt via `model.getItemsGeometry(localIds)` uit de fragment-batch gesplitst en
  als losse opaque `THREE.Mesh` gerenderd — volledig onafhankelijk van het
  fragment-materiaalsysteem. Bounding-box blijft als fallback wanneer geen
  geometrie beschikbaar is. Nagestreamde tiles worden geghost via
  `model.tiles.onItemSet`. Zie `isolateElement()` / `buildSplitOutMeshes()` in
  `viewer/src/engine/ViewerEngine.ts`.

## Project Container Model (Fase 7c)
- [x] nextcloud_client.py: constanten DIR_MODELS, DIR_VALIDATION, MANIFEST_FILENAME
- [x] nextcloud_client.py: paden migratie 99_overige_documenten → validation/, 70_BIM → models/
- [x] nextcloud_client.py: fallback logica (new path first → legacy path)
- [x] nextcloud_client.py: manifest CRUD (read, write, upsert)
- [x] volume_reader.py: fallback logica voor list_bim_files, list_output_files, get_file_path
- [x] volume_reader.py: read_manifest voor volume mount
- [x] routers/cloud.py: endpoints updaten voor nieuwe paden
- [x] routers/cloud.py: manifest endpoint (GET /api/cloud/projects/{project}/manifest)
- [x] routers/cloud.py: validation save met WefcValidation manifest update
- [x] models/cloud.py: ManifestHeader + ManifestResponse modellen
- [x] Tests: 26 tests (19 nextcloud_client + 7 cloud endpoints)

## Blocker: NC service account
- [ ] NC_SERVICE_PASS_3BM instellen in `/opt/openaec/bim-validator/.env` op server
- [ ] `sudo docker compose up -d` na .env aanmaken
- [ ] Verifieer: `curl http://localhost:8000/api/cloud/status` → `enabled: true, connected: true`

## Deploy
- [x] OIDC client registreren in Authentik
- [x] `.env` aanmaken met VITE_OIDC config
- [x] Dockerfile updaten met OIDC build args
- [x] Auth omgebouwd naar Authentik proxy headers
- [x] Project management systeem deployed (PostgreSQL + REST API)
- [x] Hybrid Nextcloud I/O deployed (volume mount + WebDAV)
- [ ] Project container model deployen (rebuild na merge)

## Testen
- [ ] Cloud: project listing via volume mount (models/ bestanden)
- [ ] Cloud: validatie save via WebDAV → zichtbaar in Nextcloud validation/
- [ ] Cloud: manifest read via GET /api/cloud/projects/{project}/manifest
- [ ] Cloud: IFC download via volume mount (performance test)
- [ ] Cloud: fallback naar legacy paden bij bestaande projecten
- [ ] Proxy auth: login via Authentik → user zichtbaar in TitleBar
- [ ] BCF ZIP downloaden → importeren in BIMcollab/Solibri/Revit
- [ ] Push issues naar BCF Platform → verifieer op platform UI
- [ ] Cross-site SSO: login validator → open platform → zelfde projecten

## Multi-tenant
- [ ] OIDC tenant claim koppelen aan tenant selectie (nu hardcoded "3bm")
- [ ] Frontend: tenant-aware API calls (tenant query param)

## Save / Save As / Open (Fase 7d)
- [x] Zustand projectIoSlice: save info tracking (source, dirty, cloudProject)
- [x] Ribbon: Project groep met Save, Save As, Open knoppen
- [x] Keyboard shortcuts: Ctrl+S (Save), Ctrl+Shift+S (Save As), Ctrl+O (Open)
- [x] SaveAsDialog: keuze lokaal/cloud, lokaal = .zip download, cloud = Nextcloud upload
- [x] OpenDialog: keuze lokaal/cloud, lokaal = file picker (.ifc/.ids/.zip), cloud = project browser
- [x] Zip support: JSZip voor lokaal opslaan (IFC + validatieresultaten) en openen (.zip extractie)
- [x] i18n: projectIo namespace (NL + EN) voor alle dialoogteksten
- [x] Icons: save, saveAs, open SVG icons in ribbon icon set
- [x] Build slaagt (npm run build)

## Fase 8: Polish & Launch
- [ ] 3BM branding
- [ ] Landing page
- [ ] SSL certificaat (automatisch via Caddy)
- [ ] Monitoring / Sentry
- [ ] Gebruikersdocumentatie
