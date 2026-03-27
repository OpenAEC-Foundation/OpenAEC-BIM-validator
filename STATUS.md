# Project Status — 2026-03-27

## Huidige fase: Fase 4 (BCF Platform Integratie) — deployed

### Wat is af
- Fase 0: Research & validatie
- Fase 1: Engine + CLI
- Fase 2: Web interface (FastAPI + React)
- Fase 3: 3D Viewer koppeling
- Deployment setup (Docker + Hetzner)
- **Fase 4: BCF Issue Management** — gebouwd + deployed
- **Fase 5: Chrome Design System** — ribbon, backstage, i18n, theming
- **Fase 6: Nextcloud Cloud Storage** — WebDAV, save/open dialog

### Gedaan in deze sessie (2026-03-27)
- Uitklapbare IFC ruimtelijke structuur in ModelBrowser
  - PropertyExtractor: `extractSpatialTree()` + `getContainedElements()` + `getAllGlobalIds()`
  - ViewerEngine: bridge methoden voor spatial tree extractie
  - CenterPanel: event handlers (spatial-tree-request/response, contained-elements-request/response)
  - SpatialSubTree component: inline boom per model met lazy-loaded element groepen
  - ModelBrowser: expand chevron per geladen model, lazy tree loading
  - Oude standalone SpatialTree component verwijderd
  - 100% client-side, geen backend dependency
- Model visibility toggle werkend (ViewerEngine ↔ store bridge)
- Element isolatie (ghost mode): selectie → alles transparant grijs, geselecteerd element opaque verdigris
  - Highlight-overlay aanpak (geen base material modificatie)
  - `isolateElement()` / `clearIsolation()` in ViewerEngine
  - CenterPanel synct automatisch met selectedElementId
- Ribbon Beeld-tab: Passend, Herstel camera, en Reset weergave knoppen werkend
- Cache-Control headers op index.html (no-cache) en /assets/ (immutable, 1yr)

### Nog te doen
- Element isolatie finetunen (testen of highlight overlay correct werkt bij grote modellen)
- BCF Platform OIDC auth (bcfSlice) nog op oude flow — aparte fix nodig
- BCF ZIP import testen in BIMcollab/Solibri/Revit
- Push issues naar BCF Platform testen
