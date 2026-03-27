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

### Gedaan in deze sessie
- Auth omgebouwd van in-app OIDC naar Authentik proxy headers
  - Backend: `/api/auth/me` endpoint (leest X-authentik-* headers)
  - Frontend: authStore gebruikt `/api/auth/me` i.p.v. oidc-client-ts flow
  - Login = page reload (proxy vangt af), logout = Authentik end-session redirect
- Oorzaak gevonden: site zit achter Authentik Forward Auth outpost,
  maar in-app OIDC redirect URI was niet geregistreerd → 400 error

### Nog te doen
- Deploy naar productie (git pull + docker compose build)
- BCF Platform OIDC auth (bcfSlice) nog op oude flow — aparte fix nodig
- BCF ZIP import testen in BIMcollab/Solibri/Revit
- Push issues naar BCF Platform testen
