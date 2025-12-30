# Fase 0: Research & Validatie - Specs

## Overzicht

**Duur:** 3-5 dagen  
**Doel:** Bewijs dat tech stack werkt voordat je investeert  
**Exit criteria:** Go/no-go besluit gedocumenteerd

---

## Spec 0.1: ifctester Proof of Concept

### Doel
Valideer dat ifctester werkt met de NL_BIM Basis ILS.

### Taken
1. Installeer ifctester in clean Python environment
2. Laad NL_BIM_Basis_ILS.ids
3. Valideer tegen een test IFC bestand
4. Inspecteer output structuur

### Code

```python
from ifctester import ids
import ifcopenshell

# Load files
ifc_model = ifcopenshell.open("test_model.ifc")
ids_file = ids.open("NL_BIM_Basis_ILS.ids")

# Validate
ids_file.validate(ifc_model)

# Inspect results
for spec in ids_file.specifications:
    print(f"{spec.name}: {len(spec.failed_elements)} failures")
```

### Acceptatiecriteria
- [ ] ifctester installeert zonder errors
- [ ] IDS file wordt geladen
- [ ] Validatie draait zonder crash
- [ ] Results zijn programmatisch toegankelijk

---

## Spec 0.2: That Open Engine Proof of Concept

### Doel
Bewijs dat IFC in browser getoond kan worden.

### Taken
1. Setup minimal React/Vite project
2. Installeer That Open Engine
3. Laad een klein IFC bestand
4. Render in viewport

### Code

```typescript
import * as OBC from "@thatopen/components";

const components = new OBC.Components();
const worlds = components.get(OBC.Worlds);
const world = worlds.create();

// Setup scene
world.scene = new OBC.SimpleScene(components);
world.renderer = new OBC.SimpleRenderer(components, container);
world.camera = new OBC.SimpleCamera(components);

// Load IFC
const ifcLoader = components.get(OBC.IfcLoader);
const model = await ifcLoader.load(ifcFile);
world.scene.three.add(model);
```

### Acceptatiecriteria
- [ ] IFC bestand laadt in browser
- [ ] 3D model is zichtbaar
- [ ] Camera controls werken
- [ ] Performance is acceptabel (<5s voor 50MB)

---

## Spec 0.3: Viewer Approach Comparison

### Doel
Vergelijk client-side vs server-side IFC rendering.

### Test Scenario's

| Bestand | Grootte | Client-side | Server-side |
|---------|---------|-------------|-------------|
| Small | 50 MB | Test | Test |
| Medium | 200 MB | Test | Test |
| Large | 500 MB | Test | Test |

### Metrics
- Load time (seconds)
- Memory usage (client)
- Memory usage (server)
- Frame rate (FPS)
- Feature support (selection, properties)

### Server-side Approach

```bash
# IfcConvert to glTF
ifcconvert model.ifc model.gltf

# Then load in Three.js
const loader = new GLTFLoader();
loader.load('model.gltf', (gltf) => scene.add(gltf.scene));
```

### Decision Matrix

| Criteria | Weight | Client | Server |
|----------|--------|--------|--------|
| Load time small | 20% | ? | ? |
| Load time large | 30% | ? | ? |
| Server cost | 20% | Low | High |
| Features | 30% | Full | Limited |

### Acceptatiecriteria
- [ ] Beide approaches getest
- [ ] Metrics gedocumenteerd
- [ ] Aanbeveling gemaakt
- [ ] Trade-offs beschreven

---

## Spec 0.4: BCF Format Research

### Doel
Begrijp BCF 2.1 structuur voor export.

### Taken
1. Download BCF 2.1 spec van buildingSMART
2. Analyseer voorbeeldbestanden
3. Identificeer minimale velden
4. Plan generator structuur

### BCF Structure

```
issue.bcf (ZIP)
├── bcf.version
├── project.bcfp (optional)
├── markup.bcf
│   ├── Topic
│   │   ├── Guid
│   │   ├── Title
│   │   ├── Description
│   │   └── CreationDate
│   └── Viewpoints
│       └── Viewpoint (ref to .bcfv)
├── viewpoint.bcfv
│   ├── PerspectiveCamera
│   │   ├── CameraViewPoint (X, Y, Z)
│   │   ├── CameraDirection
│   │   └── CameraUpVector
│   └── Components
│       └── Selection
│           └── Component (IfcGuid)
└── snapshot.png (optional)
```

### Acceptatiecriteria
- [ ] BCF spec doorgelezen
- [ ] Minimale velden geïdentificeerd
- [ ] Voorbeeld handmatig gemaakt
- [ ] Import getest in BIMcollab

---

## Spec 0.5: Go/No-Go Decision

### Doel
Formele beslissing om door te gaan.

### Checklist

| Item | Status | Blocker? |
|------|--------|----------|
| ifctester werkt | [ ] | Yes |
| That Open Engine werkt | [ ] | Yes |
| Viewer approach gekozen | [ ] | Yes |
| BCF begrepen | [ ] | No |
| Team capacity OK | [ ] | Yes |
| Budget OK | [ ] | Yes |

### Decision

**GO** als alle "Yes" blockers zijn afgevinkt.
**NO-GO** als kritieke blocker niet opgelost.

### Output
Document met:
- Research bevindingen
- Beslissing (GO/NO-GO)
- Risico's en mitigaties
- Aangepaste planning (indien nodig)
