# TODO

## Deploy (volgende sessie)
- [x] OIDC client registreren in Authentik
- [x] `.env` aanmaken met VITE_OIDC config
- [x] Dockerfile updaten met OIDC build args
- [ ] `http://localhost:8080/oidc-callback` toevoegen als redirect URI in Authentik
- [ ] Deploy: `ssh jochem@open-aec.com` → `cd /opt/bim-validator && git pull && docker compose up -d --build`
- [ ] Caddy config checken voor domein

## Testen
- [ ] OIDC login flow testen (lokaal + productie)
- [ ] BCF ZIP downloaden → importeren in BIMcollab/Solibri/Revit
- [ ] Push issues naar BCF Platform → verifieer op platform UI
- [ ] Cross-site SSO: login validator → open platform → zelfde projecten
- [ ] Project aanmaken vanuit validator → zichtbaar op platform

## Fase 5: Polish & Launch
- [ ] 3BM branding
- [ ] Landing page
- [ ] SSL certificaat (automatisch via Caddy)
- [ ] Monitoring / Sentry
- [ ] Gebruikersdocumentatie
