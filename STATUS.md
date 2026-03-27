# Project Status — 2026-03-24

## Huidige fase: Fase 4 (BCF Platform Integratie) — deployed

### Wat is af
- Fase 0: Research & validatie
- Fase 1: Engine + CLI
- Fase 2: Web interface (FastAPI + React)
- Fase 3: 3D Viewer koppeling
- Deployment setup (Docker + Hetzner)
- **Fase 4: BCF Issue Management** — gebouwd + deployed

### Gedaan in deze sessie
- Lokale BCF issue queue (aanmaken per spec/requirement/element)
- +BCF knoppen op alle drie niveaus in validatieresultaten
- "Alle failures → BCF" bulk knop
- BCF 2.1 ZIP generator (JSZip) voor lokale download
- BCF Platform integratie (push issues, project aanmaken)
- OIDC/SSO via Authentik (oidc-client-ts) + API key fallback
- BCF tab badge met issue count
- Merge conflicts opgelost met remote (i18n, ribbon UI refactor)
- OIDC client geregistreerd in Authentik (bim-validator, public client)
- .env + .env.example + Dockerfile OIDC build args
- Deploy op Hetzner gelukt (git pull + docker compose up --build)

### Nog te testen
- OIDC login flow end-to-end (lokaal + productie)
- BCF ZIP import in BIMcollab/Solibri/Revit
- Push issues naar BCF Platform → verifieer op platform UI
- Cross-site SSO: login validator → open platform → zelfde projecten
- `http://localhost:8080/oidc-callback` toevoegen als redirect URI in Authentik
