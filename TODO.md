# TODO

## Bug: Ghost mode — geselecteerd element niet opaque
- [x] Oorzaak: material-level opacity beïnvloedt alle elementen in shared meshes (IFC batching)
- [x] Fragment highlight overlay werkt niet omdat transparante materials erover heen renderen
- **Geprobeerde fixes die NIET werkten:**
  - Poging 1: mesh-level material restore → werkt niet (shared meshes)
  - Poging 2: fragment highlight overlay (opacity 1.0, RenderedFaces.TWO) → overlay niet zichtbaar
  - Poging 3: FragmentsModel.setOpacity()/resetOpacity()/setColor() → niets transparant (tile streaming?)
  - Poging 4: material ghost + depthWrite=false + highlight overlay → highlight nog steeds niet opaque
- **Nog te onderzoeken:**
  - [ ] Controleer of `fragments.highlight()` überhaupt iets rendert (console log de modelIdMap)
  - [ ] Test of `fragments.highlight()` een apart mesh aanmaakt of iets anders doet
  - [ ] Alternatief: OBC.Hider.isolate(modelIdMap) — verbergt alles behalve selected element
  - [ ] Alternatief: twee render passes — eerst ghost scene, dan selected element apart renderen
  - [ ] Alternatief: kloon de geometry van het geselecteerde element als apart THREE.Mesh met opaque material
  - [ ] Check browser console op errors tijdens isolateElement()
- Relevante code: `viewer/src/engine/ViewerEngine.ts` → `isolateElement()`

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

## Testen
- [ ] Cloud: project listing via volume mount (70_BIM bestanden)
- [ ] Cloud: BCF save via WebDAV → zichtbaar in Nextcloud
- [ ] Cloud: IFC download via volume mount (performance test)
- [ ] Proxy auth: login via Authentik → user zichtbaar in TitleBar
- [ ] BCF ZIP downloaden → importeren in BIMcollab/Solibri/Revit
- [ ] Push issues naar BCF Platform → verifieer op platform UI
- [ ] Cross-site SSO: login validator → open platform → zelfde projecten

## Multi-tenant
- [ ] OIDC tenant claim koppelen aan tenant selectie (nu hardcoded "3bm")
- [ ] Frontend: tenant-aware API calls (tenant query param)

## Fase 8: Polish & Launch
- [ ] 3BM branding
- [ ] Landing page
- [ ] SSL certificaat (automatisch via Caddy)
- [ ] Monitoring / Sentry
- [ ] Gebruikersdocumentatie
