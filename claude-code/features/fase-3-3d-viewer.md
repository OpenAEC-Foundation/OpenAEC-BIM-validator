# Fase 3: 3D Viewer Integration

## Doel
IFC model visualisatie met interactie tussen validatieresultaten en 3D view.

## Specs

### Spec 3.1 - That Open Engine Setup
- Integreer That Open Engine (@thatopen/components)
- Setup WebGL renderer in React
- Configureer scene, camera, lights
- Memory management voor grote modellen
- Loading indicator tijdens model load

### Spec 3.2 - IFC Loading
- Load IFC via web-ifc
- Streaming loading voor grote bestanden
- Progress callback tijdens laden
- Error handling voor ongeldige files
- Unload/cleanup bij nieuw bestand

### Spec 3.3 - Camera Controls
- Orbit controls (rotate, pan, zoom)
- Fit-to-model functie
- Home view reset
- Touch support voor mobile
- Keyboard shortcuts:
  - `F` - Fit to selection
  - `H` - Home view
  - `1-6` - Preset views (front, back, left, right, top, bottom)

### Spec 3.4 - Element Selection
- Click-to-select in 3D view
- Highlight geselecteerd element
- Multi-select met Ctrl/Cmd
- Deselect met Escape of click op leeg
- Selection state in React context

### Spec 3.5 - Results-Viewer Link
- Bidirectionele koppeling:
  - Klik in resultatenlijst → highlight element in viewer
  - Klik in viewer → scroll naar element in resultaten
- Shared state tussen componenten
- Element lookup via GlobalId

### Spec 3.6 - Highlight Failed Elements
- Visuele markering van gefaalde elementen
- Kleurcodering:
  - Rood: Failed
  - Groen: Passed
  - Grijs: Not checked
- Toggle om alleen failures te tonen
- Transparency voor niet-relevante elementen

## Exit Criteria
- [ ] IFC model zichtbaar in 3D
- [ ] Klik op failed element → highlight in viewer
- [ ] Klik in viewer → toon properties
- [ ] Fly-to camera op element click

## Component Architecture

```
ViewerContainer/
├── Toolbar/
│   ├── ViewControls (home, fit, presets)
│   ├── DisplayModes (wireframe, solid, xray)
│   └── FilterControls (show/hide by status)
├── Canvas/
│   └── ThatOpenEngine scene
├── PropertiesPanel/
│   ├── ElementInfo
│   ├── ValidationStatus
│   └── PropertySets
└── ViewerContext (shared state)
```

## Key Interfaces

```typescript
interface ViewerState {
  model: FragmentsGroup | null;
  selectedElements: Set<string>; // GlobalIds
  highlightedElements: Map<string, HighlightStatus>;
  camera: CameraState;
}

interface HighlightStatus {
  globalId: string;
  status: 'passed' | 'failed' | 'unchecked';
  color: string;
}

interface ViewerActions {
  loadModel(file: File): Promise<void>;
  selectElement(globalId: string): void;
  highlightElements(elements: HighlightStatus[]): void;
  flyTo(globalId: string): void;
  resetView(): void;
}
```

## That Open Engine Integration

```typescript
import * as OBC from "@thatopen/components";
import * as OBCF from "@thatopen/components-front";

// Setup
const components = new OBC.Components();
const worlds = components.get(OBC.Worlds);
const world = worlds.create();

// Renderer
world.renderer = new OBCF.PostproductionRenderer(components, container);

// Camera
world.camera = new OBC.OrthoPerspectiveCamera(components);

// Scene
world.scene = new OBC.SimpleScene(components);
world.scene.setup();

// IFC Loader
const fragments = components.get(OBC.FragmentsManager);
const fragmentIfcLoader = components.get(OBC.IfcLoader);
await fragmentIfcLoader.setup();

// Load model
const model = await fragmentIfcLoader.load(ifcBuffer);
world.scene.three.add(model);

// Selection
const highlighter = components.get(OBCF.Highlighter);
highlighter.setup({ world });
```

## Performance Considerations

- Gebruik Fragments voor grote modellen
- Lazy loading van property sets
- Culling van niet-zichtbare elementen
- LOD (Level of Detail) waar mogelijk
- Web Workers voor zware berekeningen
