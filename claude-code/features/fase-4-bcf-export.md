# Fase 4: BCF Platform Integratie

## Doel
Koppel de BIM Validator aan het OpenAEC BCF Platform zodat validatie-issues
direct opgeslagen worden per project, bekeken kunnen worden met status/overzichten,
en via Revit plugin gedownload kunnen worden door andere gebruikers.

## Context

### OpenAEC BCF Platform
- **Repo:** `openaec-bcf-platform`
- **Tech:** Rust/Axum + PostgreSQL + React
- **API:** BCF 2.1 compliant REST API op `/bcf/2.1/`
- **Auth:** OIDC (Authentik) + API keys per project (`bcfk_...`)
- **Features:** Projecten, topics, comments, viewpoints, snapshots, BCF ZIP import/export

### Design keuze: TypeScript nu, Rust `bcf-client` crate later
Geen Python BCF generator. Integratie-logica in TypeScript voor de validator web-app.

**Lange termijn:** een gedeelde Rust `bcf-client` crate (apart project) die herbruikbaar is in:
- Tauri desktop app (native)
- Solibri plugin
- Revit plugin
- CLI tools
- Browser via WASM

**Nu (fase 4):** lichtgewicht TypeScript client in de validator frontend.
Zelfde API calls, makkelijk later te vervangen door WASM-compiled `bcf-client`.

## Architectuur

```
┌─────────────────────────────────────────────────────────────────┐
│                     BIM Validator Frontend                       │
├─────────────────────────────────────────────────────────────────┤
│  ValidationPanel        │  BCF Platform Panel                   │
│  - Run validation       │  - Platform URL config                │
│  - View results         │  - API key config                     │
│  - Highlight elements   │  - Project selector                   │
│                         │  - "Push to Platform" button          │
│                         │  - Push status/progress               │
└────────┬────────────────┴──────────┬────────────────────────────┘
         │                           │
         ▼                           ▼
┌────────────────────┐    ┌──────────────────────────────────────┐
│  Validator Backend  │    │     OpenAEC BCF Platform API         │
│  (Python/FastAPI)   │    │     /bcf/2.1/projects/...            │
│  - IFC parsing      │    │     /bcf/2.1/.../topics/...          │
│  - IDS validation   │    │     /bcf/2.1/.../viewpoints/...      │
│  - Results JSON     │    │                                      │
└─────────────────────┘    └──────────────────────────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │  Revit BCF Plugin     │
                           │  (download issues)    │
                           └──────────────────────┘
```

## Specs

### Spec 4.1 - TypeScript BCF Platform Client

API client die praat met het BCF Platform:

```typescript
// lib/bcfPlatformClient.ts

interface BcfPlatformConfig {
  baseUrl: string;      // bijv. "https://bcf.openaec.com"
  apiKey: string;       // "bcfk_..." project-scoped API key
}

class BcfPlatformClient {
  constructor(config: BcfPlatformConfig);

  // Projects
  listProjects(): Promise<BcfProject[]>;
  getProject(id: string): Promise<BcfProject>;

  // Topics
  listTopics(projectId: string): Promise<BcfTopic[]>;
  createTopic(projectId: string, data: CreateTopicRequest): Promise<BcfTopic>;
  updateTopic(projectId: string, topicId: string, data: UpdateTopicRequest): Promise<BcfTopic>;

  // Comments
  createComment(projectId: string, topicId: string, data: CreateCommentRequest): Promise<BcfComment>;

  // Viewpoints
  createViewpoint(projectId: string, topicId: string, data: CreateViewpointRequest): Promise<BcfViewpoint>;
}
```

**BCF Platform API endpoints:**
- `GET    /bcf/2.1/projects` — lijst projecten
- `POST   /bcf/2.1/projects/{pid}/topics` — maak topic
- `POST   /bcf/2.1/projects/{pid}/topics/{tid}/comments` — maak comment
- `POST   /bcf/2.1/projects/{pid}/topics/{tid}/viewpoints` — maak viewpoint

**Authenticatie:** `Authorization: Bearer bcfk_...` header met project API key.

### Spec 4.2 - Validation-to-BCF Topic Mapper

Map `ValidationResult` naar BCF topics:

```typescript
// lib/validationToBcf.ts

interface TopicMapping {
  topic: CreateTopicRequest;
  comment: CreateCommentRequest;
  viewpoint: CreateViewpointRequest;
}

function mapValidationToTopics(result: ValidationResult): TopicMapping[] {
  // 1 topic per gefaalde specification
  // Groepeer gefaalde elementen per spec
}
```

**Mapping regels:**
| Validation veld | BCF Topic veld | Voorbeeld |
|----------------|---------------|-----------|
| spec.name | title | "Missing FireRating property" |
| spec.description + failed elements | description | Gedetailleerde uitleg met GlobalId's |
| spec.severity | priority | critical→High, warning→Normal |
| "IDS Validation" | topic_type | Altijd "IDS Validation" |
| "Open" | topic_status | Altijd "Open" |
| spec.ifc_entity, check type | labels | ["IfcWall", "Property Missing", "IDS"] |
| failed element GlobalId's | viewpoint.components.selection | Component references |

**Topic beschrijving format:**
```
IDS Specification: {spec_name}
IFC Entity: {entity_type}
Check: {requirement_type}

Failed elements ({count}):
- {GlobalId} — {element_name} ({element_type})
- {GlobalId} — {element_name} ({element_type})
...

Source: {ids_filename}
```

### Spec 4.3 - Viewpoint Generation

Per topic een viewpoint met component selection:

```typescript
interface CreateViewpointRequest {
  components: {
    selection: Array<{ ifc_guid: string }>;       // gefaalde elementen
    visibility: {
      default_visibility: true;
      exceptions: [];                              // alles zichtbaar
    };
    coloring: Array<{
      color: string;                               // "FF0000" rood voor failures
      components: Array<{ ifc_guid: string }>;
    }>;
  };
  // Camera optioneel - als 3D viewer actief is, capture huidige positie
  camera?: {
    camera_type: "perspective";
    position: { x: number; y: number; z: number };
    direction: { x: number; y: number; z: number };
    up: { x: number; y: number; z: number };
    field_of_view: number;
  };
}
```

**Viewpoint strategie:**
- Selection: alle gefaalde GlobalId's van de specification
- Coloring: rood (#FF0000) voor gefaalde elementen
- Camera: capture vanuit 3D viewer als beschikbaar, anders geen camera
- Snapshot: optioneel - canvas capture als PNG (later)

### Spec 4.4 - Platform UI Componenten

#### 4.4.1 - Platform Settings
```typescript
// Opgeslagen in localStorage
interface PlatformSettings {
  url: string;          // BCF Platform URL
  apiKey: string;       // Project API key
  projectId?: string;   // Laatst geselecteerde project
}
```

- Invoervelden voor URL + API key
- "Test verbinding" knop
- Persistentie in localStorage

#### 4.4.2 - Project Selector
- Dropdown met projecten van het platform
- Haalt lijst op via `GET /bcf/2.1/projects`
- Toont project naam + aantal bestaande topics

#### 4.4.3 - Push Flow
Na succesvolle validatie:
1. Gebruiker klikt "Push naar BCF Platform"
2. Kies project (of maak nieuw aan)
3. Preview: hoeveel topics worden aangemaakt
4. Bevestig → push topics één voor één
5. Progress bar met status per topic
6. Klaar → link naar project op platform

#### 4.4.4 - BCF Tab in RightPanel
- Vervang placeholder "binnenkort beschikbaar"
- Platform status (verbonden / niet verbonden)
- Laatste push info (datum, aantal topics)
- Link naar project op platform

### Spec 4.5 - BCF ZIP Download (Lokale Fallback)

Voor offline gebruik of import in andere tools:

```typescript
// lib/bcfZipGenerator.ts

async function generateBcfZip(result: ValidationResult): Promise<Blob> {
  // Genereer BCF 2.1 ZIP in browser met JSZip
  // Zelfde mapping als platform push
  // Return als downloadbare Blob
}
```

**Structuur:**
```
validation-results.bcf/
├── bcf.version
└── {topic-guid}/
    ├── markup.bcf
    └── viewpoint.bcfv
```

- Gebruikt JSZip voor ZIP generatie in browser
- Zelfde mapping logica als platform push
- Download knop naast "Push naar Platform"

### Spec 4.6 - Integration Tests

- [ ] Topics correct aangemaakt op platform
- [ ] GlobalId's komen overeen met IFC elementen
- [ ] BCF ZIP importeerbaar in BIMcollab
- [ ] BCF ZIP importeerbaar in Revit (via BCF plugin)
- [ ] Viewpoint selection werkt in ontvangende tool
- [ ] Labels en priority correct gemapped
- [ ] Grote validatie (100+ failures) werkt binnen timeout
- [ ] API key auth werkt correct
- [ ] Foutafhandeling bij platform onbereikbaar

## Dependencies

### NPM packages (toe te voegen aan viewer)
- `jszip` — BCF ZIP generatie in browser
- Geen andere nieuwe dependencies nodig (fetch API voor HTTP)

### BCF Platform vereisten
- Platform draait en is bereikbaar
- API key aangemaakt voor het project
- CORS geconfigureerd voor validator domein

## Flow: Validatie → Platform → Revit

```
1. Gebruiker upload IFC + IDS in Validator
2. Validator backend valideert → resultaten JSON
3. Frontend toont resultaten in ValidationPanel
4. Gebruiker klikt "Push naar BCF Platform"
5. Frontend mapped results → BCF topics (TypeScript)
6. Frontend pusht topics naar Platform API
7. Platform slaat op in PostgreSQL
8. Op Platform: overzichten, status tracking, dashboards
9. Andere gebruiker opent Revit → BCF plugin
10. Plugin download BCF van Platform (GET /api/v1/projects/{id}/export-bcf)
11. Issues zichtbaar in Revit met element selectie
```

## Later (niet in scope fase 4)

- **Rust `bcf-client` crate** — gedeelde API client voor alle platformen:
  - Compileert naar native (Tauri, Solibri plugin, Revit plugin, CLI)
  - Compileert naar WASM (browser, vervangt TypeScript client)
  - Leeft in eigen repo of als crate in openaec-bcf-platform workspace
- Snapshot generatie (canvas capture → PNG upload)
- Bi-directionele sync (status updates terug naar validator)
- Automatische push na validatie (zonder handmatige stap)
- Power BI-achtige dashboards op BCF Platform
- SSO doorverbinding (zelfde Authentik voor validator + platform)
- Solibri plugin — upload BCF issues naar platform
- Revit plugin — download + upload BCF issues
