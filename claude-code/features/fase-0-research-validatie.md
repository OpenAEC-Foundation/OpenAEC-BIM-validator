# Fase 0: Research & Validatie

## Doel
Bewijs dat de tech stack werkt voordat er geïnvesteerd wordt in ontwikkeling.

## Specs

### Spec 0.1 - ifctester Proof of Concept
- Installeer ifctester library
- Laad een test IFC bestand
- Valideer tegen NL_BIM_Basis_ILS.ids
- Documenteer output formaat en mogelijkheden

### Spec 0.2 - That Open Engine Proof of Concept
- Setup basic HTML/JS pagina met That Open Engine
- Laad een klein IFC bestand (<10MB)
- Verifieer dat model correct wordt weergegeven
- Test basis camera controls

### Spec 0.3 - Viewer Approach Comparison
Vergelijk twee benaderingen:

**Client-side (browser)**
- Voordelen: Geen server load, privacy-vriendelijk
- Nadelen: Beperkt door browser memory, grote files problematisch

**Server-side**
- Voordelen: Krachtigere verwerking, consistente performance
- Nadelen: Server kosten, upload tijd

Documenteer beslissing met rationale.

### Spec 0.4 - BCF Format Research
- Bestudeer BCF 2.1 specificatie
- Analyseer structuur van .bcf/.bcfzip files
- Identificeer vereiste velden voor viewpoints
- Test import in BIMcollab of andere BCF viewer

### Spec 0.5 - Go/No-Go Decision
Documenteer bevindingen en maak go/no-go beslissing gebaseerd op:
- Haalbaarheid tech stack
- Geïdentificeerde risico's
- Geschatte complexiteit

## Exit Criteria
- [ ] ifctester valideert NL_BIM Basis ILS tegen test IFC
- [ ] That Open Engine toont IFC in browser
- [ ] Viewer approach beslissing gedocumenteerd
- [ ] BCF structuur begrepen
- [ ] Go/no-go gedocumenteerd

## Deliverables
- `docs/poc/ifctester-poc.md` - POC resultaten
- `docs/poc/viewer-poc.md` - Viewer test resultaten
- `docs/decisions/viewer-approach.md` - ADR voor viewer keuze
- `docs/research/bcf-format.md` - BCF onderzoek
- `docs/decisions/go-no-go.md` - Finale beslissing
