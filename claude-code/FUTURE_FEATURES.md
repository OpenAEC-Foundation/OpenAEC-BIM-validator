# Future Features

## Backlog voor na v1.0

### Multi-Model Viewing (Federated)
- Laad meerdere IFC bestanden tegelijk
- Zie architectuur + constructie + MEP samen
- Per-model visibility toggles
- Cross-model validatie (komt element voor in beide?)

### Clash Detection
- Detecteer geometrische conflicten
- Hard clashes (doorsnijdingen)
- Soft clashes (te weinig ruimte)
- Clearance clashes (vrije ruimte eisen)
- Export clashes naar BCF

### Measurement Tools
- Afstand meten tussen punten
- Oppervlakte meten
- Volume berekenen
- Snapshot met afmetingen

### Smart Views
- Filter op classificatie
- Filter op verdieping
- Filter op property waarde
- Sla filters op als "smart view"

### Scheduling (4D)
- Koppel elementen aan planning
- Tijdlijn slider
- Animatie van bouwvolgorde

### Desktop App (Tauri)
- Tauri app met gedeelde TypeScript codebase
- Lokale verwerking (geen upload)
- Grotere bestanden (>1GB)
- Offline gebruik
- Zelfde BCF Platform integratie als web-app

### Multi-Language
- Nederlands (default)
- Engels
- Duits
- Frans

### API Rate Limiting
- Fair use policy
- Premium tier voor meer validaties
- API keys voor integraties

### Template Library
- Meer IDS templates:
  - NLRS (BIM Loket)
  - COINS
  - Gemeentelijke eisen
  - Woningcorporatie eisen
  - ISO 19650 compliance

### Integration Plugins
- Revit BCF plugin — download issues vanuit BCF Platform
- Revit add-in voor direct valideren
- ArchiCAD add-on
- BIMcollab Zoom plugin
- ACC/BIM 360 connector

### Reporting
- PDF rapportage
- Excel export
- Scheduled validatie (cron)
- Email notificaties

---

## Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Multi-Model | High | High | P2 |
| Clash Detection | High | High | P2 |
| Measurement | Medium | Low | P1 |
| Smart Views | Medium | Medium | P1 |
| Tauri Desktop App | Medium | Medium | P2 |
| Template Library | High | Low | P1 |
| PDF Reports | Medium | Low | P1 |

**P1** = Next release  
**P2** = Future release  
**P3** = Nice to have
