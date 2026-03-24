# Project Status — 2026-03-12

## Huidige fase: Fase 3 (3D Viewer) + Deployment setup

### Wat is af
- Fase 0: Research & validatie ✅
- Fase 1: Engine + CLI ✅
- Fase 2: Web interface (FastAPI + React) ✅
- Fase 3: 3D Viewer koppeling (validation ↔ viewer) ✅
- **Deployment setup**: Docker productie-config toegevoegd ✅

### Zojuist gedaan (deze sessie)
- Multi-stage `Dockerfile` (frontend build + backend in één image)
- `docker-compose.yml` met persistent volumes
- `.dockerignore` voor kleine images
- `deploy.sh` script voor Hetzner
- `server/main.py`: CORS via `CORS_ORIGINS` env var + SPA static file serving
- Alles gepusht naar GitHub

### Server status
- Hetzner server: actief, maar SSH (poort 22) geblokkeerd door firewall
- Caddy draait al op de server als reverse proxy
- Deployment moet handmatig via server terminal (SSH firewall openen of console)

### Volgende stap
- Deploy op Hetzner (zie TODO.md)
- Fase 4: BCF Export
