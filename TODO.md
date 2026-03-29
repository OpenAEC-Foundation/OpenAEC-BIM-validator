# TODO

## Bug: Ghost mode — geselecteerd element niet opaque
- [x] Oorzaak: material-level opacity beïnvloedt alle elementen in shared meshes (IFC batching)
- [x] Fragment highlight overlay werkt niet omdat transparante materials erover heen renderen
- [x] Fix: FragmentsModel.setOpacity() / resetOpacity() / setColor() per element (fragment-level)
- [x] Verwijderd: savedMaterials map, allGuidsCache, restoreMaterials(), material traversal

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
