# IFC Validator Roadmap

## Fase Overzicht

| Fase | Naam | Duur | Exit Criteria |
|------|------|------|---------------|
| 0 | Research & Validatie | 3-5 dagen | Go/no-go besluit |
| 1 | Engine + CLI | 1 week | CLI valideert IFC tegen IDS |
| 2 | Web Interface | 1 week | Browser upload + results |
| 3 | 3D Viewer | 1-2 weken | Click-to-select in viewer |
| 4 | BCF Export | 3-5 dagen | Download BCF file |
| 5 | Launch | 3-5 dagen | Live op productie |

---

## Fase 0: Research & Validatie

**Doel:** Bewijs dat tech stack werkt voordat je investeert

### Specs
1. **Spec 0.1** - ifctester Proof of Concept
2. **Spec 0.2** - That Open Engine Proof of Concept
3. **Spec 0.3** - Viewer Approach Comparison (client vs server)
4. **Spec 0.4** - BCF Format Research
5. **Spec 0.5** - Go/No-Go Decision

### Exit Criteria
- [ ] ifctester valideert NL_BIM Basis ILS tegen test IFC
- [ ] That Open Engine toont IFC in browser
- [ ] Viewer approach beslissing gedocumenteerd
- [ ] BCF structuur begrepen
- [ ] Go/no-go gedocumenteerd

---

## Fase 1: Engine + CLI

**Doel:** Standalone validatie-engine met command-line interface

### Specs
1. **Spec 1.1** - Project Setup
2. **Spec 1.2** - IFC Parser Module
3. **Spec 1.3** - IDS Validator Module
4. **Spec 1.4** - Result Models
5. **Spec 1.5** - CLI Tool
6. **Spec 1.6** - Unit Tests

### Exit Criteria
- [ ] `pip install ifc-validator` werkt
- [ ] `ifc-validate model.ifc --ids rules.ids` output JSON/HTML
- [ ] 80%+ test coverage
- [ ] Documentatie in README

---

## Fase 2: Web Interface

**Doel:** Browser-based validatie (nog zonder 3D)

### Specs
1. **Spec 2.1** - FastAPI Setup
2. **Spec 2.2** - File Upload Endpoint
3. **Spec 2.3** - Validation Worker
4. **Spec 2.4** - Results API
5. **Spec 2.5** - Simple Frontend
6. **Spec 2.6** - Docker Compose

### Exit Criteria
- [ ] Upload IFC + IDS in browser
- [ ] Zie resultaten na validatie
- [ ] Docker compose up werkt
- [ ] Endpoint documentatie in Swagger

---

## Fase 3: 3D Viewer Integration

**Doel:** IFC model visualisatie met interactie

### Specs
1. **Spec 3.1** - That Open Engine Setup
2. **Spec 3.2** - IFC Loading
3. **Spec 3.3** - Camera Controls
4. **Spec 3.4** - Element Selection
5. **Spec 3.5** - Results-Viewer Link
6. **Spec 3.6** - Highlight Failed Elements

### Exit Criteria
- [ ] IFC model zichtbaar in 3D
- [ ] Klik op failed element → highlight in viewer
- [ ] Klik in viewer → toon properties
- [ ] Fly-to camera op element click

---

## Fase 4: BCF Export

**Doel:** Export validatie issues als BCF file

### Specs
1. **Spec 4.1** - BCF 2.1 Generator
2. **Spec 4.2** - Viewpoint Generation
3. **Spec 4.3** - Issue Mapping
4. **Spec 4.4** - Download Endpoint
5. **Spec 4.5** - Integration Tests

### Exit Criteria
- [ ] BCF file importeerbaar in BIMcollab
- [ ] Viewpoint toont gefaald element
- [ ] Issue title/description zinvol
- [ ] Batch export van meerdere issues

---

## Fase 5: Polish & Launch

**Doel:** Production-ready release

### Specs
1. **Spec 5.1** - 3BM Branding
2. **Spec 5.2** - Landing Page
3. **Spec 5.3** - Documentation
4. **Spec 5.4** - Production Deploy
5. **Spec 5.5** - Monitoring Setup

### Exit Criteria
- [ ] Live op validator.3bm.nl (of vergelijkbaar)
- [ ] SSL certificaat actief
- [ ] Uptime monitoring
- [ ] Error tracking in Sentry
- [ ] Gebruikersdocumentatie online

---

## Memory Requirements

| Scenario | IFC Size | RAM Required |
|----------|----------|--------------|
| Small model | 50 MB | ~500 MB |
| Medium model | 200 MB | ~2 GB |
| Large model | 500 MB | ~5 GB |
| Very large | 1 GB | ~10 GB |

**Server sizing:** Hetzner AX102 met 128GB kan 10+ concurrent large models aan.

---

## Ontwikkelstrategie

1. **Web-first:** Start met browser interface
2. **Desktop later:** Als power users grote bestanden lokaal willen verwerken
3. **Iteratief:** Elke fase levert werkend product

---

## Future Features (backlog)

- Multi-model viewing (federated)
- Clash detection
- Measurement tools
- Smart views
- Scheduling
- Desktop app voor offline gebruik
