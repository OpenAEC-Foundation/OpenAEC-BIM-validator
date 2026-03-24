# TODO

## Deployment (nu)
- [ ] SSH firewall openen op Hetzner OF via web console inloggen
- [ ] Op server: `git clone https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator.git /opt/bim-validator`
- [ ] `cd /opt/bim-validator && docker compose up -d --build`
- [ ] Caddy config toevoegen voor domein (bv. `bim.3bm.nl { reverse_proxy 127.0.0.1:8000 }`)
- [ ] `sudo systemctl reload caddy`
- [ ] Testen of alles werkt via browser

## Fase 4: BCF Export
- [ ] BCF 2.1 generator
- [ ] Viewpoint generation vanuit 3D viewer
- [ ] Issue mapping (validation results → BCF topics)
- [ ] Download endpoint
- [ ] Integration tests

## Fase 5: Polish & Launch
- [ ] 3BM branding
- [ ] Landing page
- [ ] SSL certificaat (automatisch via Caddy)
- [ ] Monitoring / Sentry
- [ ] Gebruikersdocumentatie
