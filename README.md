# IFC Validator Project - 3BM Bouwkunde

## Quick Start (Lokaal Testen)

```bash
# 1. Maak virtual environment
cd C:\IDS\test
python -m venv venv
venv\Scripts\activate

# 2. Installeer dependencies
pip install ifcopenshell ifctester

# 3. Test of het werkt
python test_ifctester.py
```

**Als de test slaagt → je kunt verder bouwen!**

---

## Folder Structuur

```
C:\IDS\
├── README.md                      ← Dit bestand
├── AUTO_CLAUDE_SETUP.md           ← Handleiding (lokaal, zonder git)
├── CLAUDE.md                      ← Context voor Claude Code
│
├── test/                          ← 🆕 Test folder
│   └── test_ifctester.py         ← Test script om te starten
│
├── ids-bestanden/                 ← IDS specificaties
│   ├── NL_BIM_Basis_ILS_v2.ids   ← 13 checks, NL standaard
│   └── RVB_BIM_Norm_v1.1.ids     ← 30 checks, Rijksvastgoed
│
├── claude-code/                   ← Development documentatie
│   ├── PROJECT_CONTEXT.md        ← Volledige project info
│   ├── ROADMAP.md                ← Fase planning
│   ├── ARCHITECTURE_DECISIONS.md ← Technische beslissingen
│   ├── specs/                    ← Specs per fase
│   └── fixtures/                 ← Test bestanden
│
└── webpagina/                     ← UI mockup
    └── index.html                ← 3BM branded preview
```

---

## Stap-voor-Stap

### Stap 1: Test de Basis
```bash
cd C:\IDS\test
python -m venv venv
venv\Scripts\activate
pip install ifcopenshell ifctester
python test_ifctester.py
```

### Stap 2: Test met Eigen IFC
Plaats een `.ifc` bestand in `C:\IDS\test\` en run het script opnieuw.

### Stap 3: Start Claude Code
```bash
cd C:\IDS
claude
```
Claude leest automatisch `CLAUDE.md` en kent de context.

### Stap 4: Bouw Verder
Vraag Claude om te beginnen met Phase 1 volgens de specs.

---

## Geen Git Nodig

Je kunt volledig lokaal werken. Git is pas nodig als je:
- Code wilt delen met anderen
- Naar productie wilt deployen
- Versiebeheer wilt

**Backup tip:** Kopieer werkende versies naar een backup folder.

---

## Nederlandse BIM Standaarden

De IFC Validator ondersteunt ingebouwde Nederlandse BIM standaarden, zodat je IFC-modellen kunt valideren zonder externe IDS-bestanden te zoeken.

### Beschikbare Standaard Shortcuts

| Shortcut | Standaard | Beschrijving |
|----------|-----------|--------------|
| `--ids nl-bim` | NL_BIM Basis ILS v2 | Nederlandse basis informatieleveringsspecificatie |
| `--ids rvb` | RVB BIM Norm v1.1 | Rijksvastgoedbedrijf BIM Norm voor rijkshuisvesting |

### Gebruik

Valideer een IFC-bestand met een Nederlandse standaard:

```bash
# Valideren met NL_BIM Basis ILS
python -m ifc_validator.cli validate mijn_model.ifc --ids nl-bim

# Valideren met RVB BIM Norm
python -m ifc_validator.cli validate mijn_model.ifc --ids rvb

# JSON output voor rapportage
python -m ifc_validator.cli validate mijn_model.ifc --ids nl-bim --output json

# Eigen IDS-bestand gebruiken (blijft ook werken)
python -m ifc_validator.cli validate mijn_model.ifc --ids pad/naar/eigen.ids
```

### NL_BIM Basis ILS v2

De NL_BIM Basis ILS is de Nederlandse standaard informatieleveringsspecificatie voor BIM-modellen, ontwikkeld volgens de richtlijnen van BIM Loket. Deze baseline standaard zorgt voor consistente, uitwisselbare BIM-modellen in de Nederlandse bouwsector.

#### Scope

De standaard valideert modellen op drie hoofdgebieden:

1. **Naamgevingsconventies** - Consistente naamgeving voor verdiepingen, deuren en andere elementen
2. **Classificatie & Materialen** - NL/SfB classificatie en materiaalspecificaties
3. **Technische eigenschappen** - Constructieve, thermische en brandtechnische eigenschappen

#### Volledige Dekking (12 Specificaties)

| Code | Specificatie | Wat wordt gecontroleerd |
|------|-------------|------------------------|
| 3.3 | Verdiepingsnaamgeving | Bouwlagen volgen patroon: -01, 00, 01, 02, etc. |
| 3.4 | Vermijd IfcBuildingElementProxy | Geen proxy-elementen; gebruik correcte IFC-entiteiten |
| 3.5 | Deurnaamgeving | Deuren volgen patroon: D-001, D-002, etc. |
| 3.6 | NL/SfB Classificatie | Alle objecten hebben NL/SfB (4 cijfers) classificatie |
| 4.1 | Ruimte attributen | IfcSpace bevat Name, LongName en NetFloorArea |
| 4.3 | LoadBearing wanden | Wanden hebben LoadBearing property (TRUE/FALSE) |
| 4.4 | IsExternal wanden | Wanden hebben IsExternal property (TRUE/FALSE) |
| 4.5 | Brandwerendheid | Interne dragende wanden hebben FireRating (30/60/90/120) |
| 4.6 | ThermalTransmittance | Externe wanden hebben U-waarde (W/m²K) |
| 4.7.1 | Materiaal verplicht | Alle objecten hebben materiaal toegekend |
| 4.7.2 | Materialen dragende wanden | Dragende wanden: Beton, Kalkzandsteen, Metselwerk of Staal |
| 4.8 | Renovatiestatus MEP | MEP-elementen: Bestaand, Nieuw of Te slopen |

#### Technische Details

- **IFC Versies:** IFC2X3 en IFC4
- **Aantal specificaties:** 12 checks
- **Bron:** Gebaseerd op [BIM Basis ILS](https://www.bimloket.nl/p/223/BIM-basis-ILS) van BIM Loket
- **PropertySets:** Pset_WallCommon, Qto_SpaceBaseQuantities, Pset_Condition

#### Wanneer Gebruiken?

Gebruik `--ids nl-bim` voor:
- Algemene bouwprojecten in Nederland
- Projecten die de BIM Basis ILS volgen
- Initiële modelvalidatie voordat specifiekere normen worden toegepast
- Controle van basisinformatie-uitwisseling tussen disciplines

### RVB BIM Norm v1.1

De RVB BIM Norm is de BIM standaard van het Rijksvastgoedbedrijf voor rijkshuisvestingsprojecten. Deze uitgebreidere norm controleert:

- **Project informatie** (2.2.7.1) - Projectnaam en beschrijving
- **Terrein informatie** (2.2.7.2) - Locatie, coördinaten en kadastrale gegevens
- **Gebouw informatie** (2.2.7.3) - RVB gebouwnummer
- **Bouwlaag naamgeving** (2.2.7.4) - RVB-naamgevingsconventie
- **Ruimte attributen** (2.2.7.6) - Uitgebreide ruimte-informatie
- **En meer...** - Aanvullende eisen voor rijkshuisvesting

**Geschikt voor:** IFC2X3 en IFC4
**Aantal specificaties:** 30+ checks
**Wanneer gebruiken:** Projecten voor het Rijksvastgoedbedrijf of rijkshuisvesting

### Welke Standaard Kiezen?

| Situatie | Aanbevolen Standaard |
|----------|---------------------|
| Algemeen BIM-project in Nederland | `--ids nl-bim` |
| Rijksvastgoedbedrijf / overheidsgebouwen | `--ids rvb` |
| Eigen projectspecificaties | `--ids pad/naar/eigen.ids` |
| Beide standaarden tegelijk controleren | Voer beide commands uit |

---

## Links

- [IfcOpenShell](https://ifcopenshell.org/)
- [ifctester Docs](https://docs.ifcopenshell.org/ifctester.html)
- [That Open Engine](https://thatopen.com/)
- [IDS Specification](https://technical.buildingsmart.org/projects/information-delivery-specification-ids/)
- [BIM Loket - BIM Basis ILS](https://www.bimloket.nl/p/223/BIM-basis-ILS)
- [RVB BIM Norm](https://www.rijksvastgoedbedrijf.nl/)

---

© 2025 3BM Bouwkunde - Ingenieurs van oplossingen
