# Fase 5: Polish & Launch

## Doel
Production-ready release met 3BM branding en monitoring.

## Specs

### Spec 5.1 - 3BM Branding
- Implementeer 3BM huisstijl
- Kleuren:
  - Magic Violet: #350E35 (primary)
  - Verdigris: #44B6A8 (accent)
  - Friendly Yellow: #EFBD75 (highlight)
  - Warm Magenta: #A01C48 (error/warning)
  - Flaming Peach: #DB4C40 (alert)
- Logo integratie
- Favicon en meta tags
- Consistent typography
- Dark mode support (optional)

### Spec 5.2 - Landing Page
- Hero sectie met tool uitleg
- Features overzicht
- How-to stappen
- Open source badge/link
- Footer met 3BM info
- Responsive design
- SEO optimalisatie:
  - Meta descriptions
  - OpenGraph tags
  - Structured data

### Spec 5.3 - Documentation
- User documentation:
  - Getting started guide
  - IDS bestand uitleg
  - FAQ sectie
- API documentation:
  - Swagger/OpenAPI (auto-generated)
  - Authentication (indien van toepassing)
  - Rate limits
- Developer docs:
  - Local development setup
  - Contributing guide
  - Architecture overview

### Spec 5.4 - Production Deploy
- Hetzner server setup
- Domain configuratie (validator.3bm.nl)
- nginx configuratie:
  - SSL/TLS (Let's Encrypt)
  - Reverse proxy
  - Static file serving
  - Gzip compression
  - Security headers
- Docker deployment:
  - Production compose file
  - Resource limits
  - Restart policies
- Backup strategie voor Redis data

### Spec 5.5 - Monitoring Setup
- Uptime monitoring (UptimeRobot of vergelijkbaar)
- Error tracking (Sentry)
  - Python SDK voor backend
  - JavaScript SDK voor frontend
  - Source maps upload
- Logging:
  - Structured JSON logs
  - Log rotation
  - Centralized logging (optional)
- Metrics (optional):
  - Prometheus metrics endpoint
  - Grafana dashboards
- Alerts:
  - Downtime alerts
  - Error rate alerts
  - Memory/CPU alerts

## Exit Criteria
- [ ] Live op validator.3bm.nl (of vergelijkbaar)
- [ ] SSL certificaat actief
- [ ] Uptime monitoring
- [ ] Error tracking in Sentry
- [ ] Gebruikersdocumentatie online

## Infrastructure

### nginx Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name validator.3bm.nl;

    ssl_certificate /etc/letsencrypt/live/validator.3bm.nl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/validator.3bm.nl/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Frontend
    location / {
        root /var/www/validator/frontend;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 1G;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
    }
}
```

### Production Docker Compose
```yaml
version: '3.8'

services:
  api:
    image: 3bm/ifc-validator:latest
    restart: unless-stopped
    environment:
      - REDIS_URL=redis://redis:6379
      - SENTRY_DSN=${SENTRY_DSN}
      - ENVIRONMENT=production
    volumes:
      - temp_files:/tmp/ifc_validator
    deploy:
      resources:
        limits:
          memory: 16G
        reservations:
          memory: 4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  temp_files:
  redis_data:
```

### Sentry Setup
```python
# Backend
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "development"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
)
```

```typescript
// Frontend
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  integrations: [new Sentry.BrowserTracing()],
  tracesSampleRate: 0.1,
});
```

## Launch Checklist

### Pre-launch
- [ ] All tests passing
- [ ] Security audit completed
- [ ] Performance testing done
- [ ] Documentation reviewed
- [ ] Backup system tested

### Launch Day
- [ ] DNS configured
- [ ] SSL certificate active
- [ ] Monitoring active
- [ ] Error tracking active
- [ ] Smoke tests passed

### Post-launch
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Gather user feedback
- [ ] Plan iteration based on feedback
