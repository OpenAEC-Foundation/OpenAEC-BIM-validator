# Fase 2: Web Interface

## Doel
Browser-based validatie (nog zonder 3D viewer).

## Specs

### Spec 2.1 - FastAPI Setup
- `web/app.py` - Main FastAPI application
- CORS configuratie voor frontend
- Health check endpoint
- OpenAPI/Swagger documentatie
- Structured logging

### Spec 2.2 - File Upload Endpoint
- `POST /api/v1/validate`
- Accept multipart form data:
  - `ifc_file` - IFC bestand (required)
  - `ids_file` - IDS bestand (optional, default naar NL_BIM)
- File size limits (max 1GB)
- Validatie van file types
- Temporary file storage met cleanup

### Spec 2.3 - Validation Worker
- Async validatie verwerking
- Background task voor grote bestanden
- Progress tracking (optional)
- Memory management:
  - Monitor memory usage
  - Cleanup na validatie
  - Reject als server overloaded

### Spec 2.4 - Results API
- `GET /api/v1/results/{job_id}` - Haal resultaten op
- `GET /api/v1/results/{job_id}/summary` - Alleen samenvatting
- Response models met Pydantic
- Caching van resultaten (Redis)
- TTL voor resultaten (bijv. 1 uur)

### Spec 2.5 - Simple Frontend
- React + TypeScript setup met Vite
- TailwindCSS voor styling
- Componenten:
  - `FileUpload` - Drag & drop upload
  - `ValidationProgress` - Voortgangsindicator
  - `ResultsTable` - Tabel met resultaten
  - `ResultDetail` - Detail view per requirement
- 3BM branding (basis)

### Spec 2.6 - Docker Compose
- Services:
  - `api` - FastAPI backend
  - `redis` - Cache/queue
  - `nginx` - Reverse proxy (optional voor dev)
- Volumes voor temp files
- Environment configuratie
- Health checks

## Exit Criteria
- [ ] Upload IFC + IDS in browser
- [ ] Zie resultaten na validatie
- [ ] Docker compose up werkt
- [ ] Endpoint documentatie in Swagger

## API Endpoints

```
POST   /api/v1/validate              Upload en valideer
GET    /api/v1/results/{job_id}      Haal resultaten op
GET    /api/v1/results/{job_id}/summary  Korte samenvatting
GET    /api/v1/ids                   Lijst beschikbare IDS files
GET    /health                       Health check
```

## Request/Response Examples

### Upload Request
```http
POST /api/v1/validate
Content-Type: multipart/form-data

ifc_file: <binary>
ids_file: <binary> (optional)
```

### Upload Response
```json
{
  "job_id": "abc123",
  "status": "processing",
  "message": "Validation started"
}
```

### Results Response
```json
{
  "job_id": "abc123",
  "status": "completed",
  "result": {
    "file_name": "model.ifc",
    "ids_name": "NL_BIM_Basis_ILS",
    "passed": false,
    "total_specs": 45,
    "passed_specs": 42,
    "failed_specs": 3,
    "specifications": [...]
  }
}
```

## Frontend Structure
```
frontend/
  src/
    components/
      FileUpload.tsx
      ValidationProgress.tsx
      ResultsTable.tsx
      ResultDetail.tsx
    hooks/
      useValidation.ts
    api/
      client.ts
    App.tsx
    main.tsx
  tailwind.config.js
  vite.config.ts
```

## Docker Compose
```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    volumes:
      - temp_files:/tmp/ifc_validator
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  temp_files:
  redis_data:
```
