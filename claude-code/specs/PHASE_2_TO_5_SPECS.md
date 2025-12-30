# Fase 2-5: Web, 3D, BCF, Launch - Specs

---

# Fase 2: Web Interface

**Duur:** 1 week  
**Doel:** Browser-based validatie (nog zonder 3D)  
**Exit criteria:** Upload IFC + IDS → zie resultaten in browser

---

## Spec 2.1: FastAPI Setup

### Code

```python
# src/ifc_validator/web/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="IFC Validator API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
```

### Acceptatiecriteria
- [ ] `/api/health` returns 200
- [ ] `/docs` toont Swagger UI
- [ ] CORS werkt voor localhost

---

## Spec 2.2: Validation Endpoint

### Code

```python
@router.post("/api/validate")
async def validate(
    ifc_file: UploadFile,
    ids_file: UploadFile,
):
    if not ifc_file.filename.endswith(".ifc"):
        raise HTTPException(400, "IFC file required")
    
    ifc_bytes = await ifc_file.read()
    ids_bytes = await ids_file.read()
    
    parser = IfcParser.from_bytes(ifc_bytes)
    validator = IdsValidator.from_bytes(ids_bytes)
    result = validator.validate(parser)
    
    return result.model_dump()
```

### Acceptatiecriteria
- [ ] Upload werkt met valid files
- [ ] Duidelijke error bij invalid files
- [ ] Response bevat alle specification results

---

## Spec 2.3: Simple Frontend

### Code

```html
<!DOCTYPE html>
<html>
<head>
    <title>3BM IFC Validator</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-8">
    <div class="max-w-4xl mx-auto">
        <h1 class="text-3xl font-bold mb-8">IFC Validator</h1>
        
        <form id="upload-form" class="bg-white p-6 rounded-lg shadow mb-8">
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label class="block mb-2">IFC File</label>
                    <input type="file" name="ifc_file" accept=".ifc" required>
                </div>
                <div>
                    <label class="block mb-2">IDS File</label>
                    <input type="file" name="ids_file" accept=".ids" required>
                </div>
            </div>
            <button type="submit" class="bg-blue-600 text-white px-6 py-2 rounded">
                Validate
            </button>
        </form>
        
        <div id="results" class="hidden"></div>
    </div>
</body>
</html>
```

### Acceptatiecriteria
- [ ] Form submit werkt
- [ ] Loading state zichtbaar
- [ ] Results tonen pass/fail per spec
- [ ] Failed elements expandable

---

## Spec 2.4: Docker Compose

### Code

```yaml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
    environment:
      - UPLOAD_DIR=/app/uploads
    
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - api
```

### Acceptatiecriteria
- [ ] `docker compose up` werkt
- [ ] API bereikbaar op :8000
- [ ] Frontend bereikbaar op :3000

---

# Fase 3: 3D Viewer Integration

**Duur:** 1-2 weken  
**Doel:** IFC model visualisatie met interactie  
**Exit criteria:** Click-to-select in viewer werkt

---

## Spec 3.1: That Open Engine Setup

### Code

```typescript
// frontend/src/components/Viewer.tsx
import * as OBC from "@thatopen/components";
import { useEffect, useRef } from "react";

export function Viewer({ ifcUrl, onSelect }) {
    const containerRef = useRef<HTMLDivElement>(null);
    
    useEffect(() => {
        if (!containerRef.current) return;
        
        const components = new OBC.Components();
        const worlds = components.get(OBC.Worlds);
        const world = worlds.create();
        
        world.scene = new OBC.SimpleScene(components);
        world.renderer = new OBC.SimpleRenderer(components, containerRef.current);
        world.camera = new OBC.SimpleCamera(components);
        
        // Setup picking
        const picker = components.get(OBC.Picker);
        picker.onPick.add((result) => onSelect(result.elements));
        
        return () => components.dispose();
    }, []);
    
    return <div ref={containerRef} className="w-full h-full" />;
}
```

### Acceptatiecriteria
- [ ] IFC laadt in viewer
- [ ] Camera controls werken
- [ ] Element selection werkt

---

## Spec 3.2: Highlight Failed Elements

### Code

```typescript
// Highlight failed elements in red
function highlightElements(guids: string[], color: string) {
    const highlighter = components.get(OBC.Highlighter);
    const fragments = components.get(OBC.FragmentsManager);
    
    for (const guid of guids) {
        const expressId = guidToExpressId[guid];
        if (expressId) {
            highlighter.highlight("failed", expressId, true);
        }
    }
}
```

### Acceptatiecriteria
- [ ] Failed elements rood gehighlight
- [ ] Click op element toont properties
- [ ] Fly-to werkt op click

---

# Fase 4: BCF Export

**Duur:** 3-5 dagen  
**Doel:** Export validatie issues als BCF file  
**Exit criteria:** BCF importeerbaar in BIMcollab

---

## Spec 4.1: BCF Generator

### Code

```python
# src/ifc_validator/bcf/generator.py
import zipfile
from uuid import uuid4
from xml.etree import ElementTree as ET

class BcfGenerator:
    def __init__(self, validation_result: ValidationResult):
        self.result = validation_result
    
    def generate(self, output_path: Path) -> None:
        with zipfile.ZipFile(output_path, 'w') as bcf:
            # Version file
            bcf.writestr("bcf.version", self._version_xml())
            
            # One topic per failed spec
            for spec in self.result.specifications:
                if spec.status == "fail":
                    topic_guid = str(uuid4())
                    bcf.writestr(f"{topic_guid}/markup.bcf", 
                                self._topic_xml(spec, topic_guid))
```

### Acceptatiecriteria
- [ ] Valid BCF 2.1 ZIP
- [ ] One issue per failed spec
- [ ] Viewpoint met camera positie
- [ ] Element selection in viewpoint

---

# Fase 5: Polish & Launch

**Duur:** 3-5 dagen  
**Doel:** Production-ready release  
**Exit criteria:** Live op productie

---

## Spec 5.1: 3BM Branding

### Kleuren
```css
:root {
    --magic-violet: #350E35;
    --verdigris: #44B6A8;
    --friendly-yellow: #EFBD75;
    --warm-magenta: #A01C48;
    --flaming-peach: #DB4C40;
}
```

### Font
- Primary: Gotham Bold
- Secondary: Gotham Medium
- Body: Gotham Book
- Fallback: Helvetica

### Acceptatiecriteria
- [ ] 3BM logo in header
- [ ] Brand colors toegepast
- [ ] Font styling correct

---

## Spec 5.2: Production Deploy

### Hetzner Setup

```bash
# Server: AX102, 128GB RAM
# OS: Ubuntu 24.04

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone repo
git clone https://github.com/3bm/ifc-validator.git

# Deploy
cd ifc-validator
docker compose -f docker-compose.prod.yml up -d
```

### nginx Config

```nginx
server {
    listen 443 ssl http2;
    server_name validator.3bm.nl;
    
    ssl_certificate /etc/letsencrypt/live/validator.3bm.nl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/validator.3bm.nl/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        client_max_body_size 1G;
    }
}
```

### Acceptatiecriteria
- [ ] Live op validator.3bm.nl
- [ ] SSL actief
- [ ] 1GB uploads werken
- [ ] Monitoring actief
