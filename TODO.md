# TODO

## Deploy
- [x] OIDC client registreren in Authentik
- [x] `.env` aanmaken met VITE_OIDC config
- [x] Dockerfile updaten met OIDC build args
- [x] Auth omgebouwd naar Authentik proxy headers (geen redirect URI nodig)
- [ ] Deploy: `ssh jochem@bim.open-aec.com` → `cd /opt/openaec/bim-validator && sudo git pull && sudo docker compose build --no-cache && sudo docker compose up -d`

## Testen
- [ ] Element isolatie: ghost mode testen met grote/meerdere modellen
- [ ] Proxy auth: login via Authentik → user zichtbaar in TitleBar
- [ ] BCF ZIP downloaden → importeren in BIMcollab/Solibri/Revit
- [ ] Push issues naar BCF Platform → verifieer op platform UI
- [ ] Cross-site SSO: login validator → open platform → zelfde projecten
- [ ] Project aanmaken vanuit validator → zichtbaar op platform

## BCF Platform Auth
- [ ] bcfSlice OIDC flow fixen (aparte client, redirect URI registreren) of omzetten naar proxy-based tokens

## Fase 5: Polish & Launch
- [ ] 3BM branding
- [ ] Landing page
- [ ] SSL certificaat (automatisch via Caddy)
- [ ] Monitoring / Sentry
- [ ] Gebruikersdocumentatie
