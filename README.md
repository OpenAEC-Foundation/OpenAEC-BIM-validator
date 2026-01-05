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

De RVB BIM Norm is de BIM standaard van het Rijksvastgoedbedrijf voor rijkshuisvestingsprojecten. Deze uitgebreide norm stelt hogere eisen dan de basis ILS en is specifiek ontwikkeld voor overheidsgebouwen en rijkshuisvesting.

#### Scope

De standaard valideert modellen op vijf hoofdgebieden:

1. **Project & Locatie** - Projectgegevens, terreinlocatie met coördinaten, gebouwinformatie met RVB-nummering
2. **Ruimtes & Zones** - Uitgebreide ruimteattributen, hoeveelheden, en zone-informatie
3. **NL-SfB Classificatie** - Verplichte classificatie voor alle hoofdelementen (wanden, vloeren, daken, deuren, ramen, kolommen, balken, trappen)
4. **Constructieve & Brandtechnische eigenschappen** - LoadBearing, IsExternal, FireRating, vluchtdeuren
5. **Model kwaliteit** - Geen proxy-elementen, materiaal verplicht, meubilair classificatie

#### Volledige Dekking (27 Specificaties)

**Project & Locatie Informatie (4 specs)**

| Code | Specificatie | Wat wordt gecontroleerd |
|------|-------------|------------------------|
| 2.2.7.1 | Project informatie | IfcProject bevat Name en LongName |
| 2.2.7.2 | Terrein informatie | IfcSite met Name, RefLatitude, RefLongitude, RefElevation |
| 2.2.7.3 | Gebouw informatie | IfcBuilding met Name en BuildingID (RVB-nummer) |
| 2.2.7.4 | Bouwlaag naamgeving | Verdiepingen volgen RVB-patroon: "-01 Kelder", "00 BG", "01 Eerste", etc. |

**Ruimtes & Zones (3 specs)**

| Code | Specificatie | Wat wordt gecontroleerd |
|------|-------------|------------------------|
| 2.2.7.6a | Ruimte attributen | IfcSpace met Name, ObjectType, LongName en IsExternal |
| 2.2.7.6b | Ruimte hoeveelheden | NetFloorArea, GrossFloorArea en Height in Qto_SpaceBaseQuantities |
| 2.2.7.7 | Zone informatie | IfcZone met Name en ObjectType |

**NL-SfB Classificatie (8 specs)**

| Code | Specificatie | Wat wordt gecontroleerd |
|------|-------------|------------------------|
| 2.2.6.2a | NL-SfB Wanden | IfcWall met NL-SfB classificatie (21.xx) |
| 2.2.6.2b | NL-SfB Vloeren | IfcSlab met NL-SfB classificatie (23.xx) |
| 2.2.6.2c | NL-SfB Daken | IfcRoof met NL-SfB classificatie (27.xx) |
| 2.2.6.2d | NL-SfB Deuren | IfcDoor met NL-SfB classificatie (31.xx) |
| 2.2.6.2e | NL-SfB Ramen | IfcWindow met NL-SfB classificatie (31.xx) |
| 2.2.6.2f | NL-SfB Kolommen | IfcColumn met NL-SfB classificatie (28.xx) |
| 2.2.6.2g | NL-SfB Balken | IfcBeam met NL-SfB classificatie (28.xx) |
| 2.2.6.2h | NL-SfB Trappen | IfcStair met NL-SfB classificatie (24.xx) |

**Constructieve & Brandtechnische Eigenschappen (9 specs)**

| Code | Specificatie | Wat wordt gecontroleerd |
|------|-------------|------------------------|
| 2.2.7.8a | Element materiaal | Alle bouwelementen hebben materiaal toegekend |
| 2.2.7.8b | IsExternal wanden | Wanden hebben IsExternal property (Pset_WallCommon) |
| 2.2.7.8.1a | FireRating wanden | Wanden hebben FireRating (brandwerendheid in minuten) |
| 2.2.7.8.1b | FireRating deuren | Deuren hebben FireRating én SelfClosing property |
| 2.2.7.8.1c | Vluchtdeuren | Deuren hebben FireExit property (TRUE/FALSE) |
| 2.2.7.8.2a | LoadBearing wanden | Wanden hebben LoadBearing property (Pset_WallCommon) |
| 2.2.7.8.2b | LoadBearing vloeren | Vloeren hebben LoadBearing property (Pset_SlabCommon) |
| 2.2.7.8.2c | LoadBearing kolommen | Kolommen hebben LoadBearing property (Pset_ColumnCommon) |
| 2.2.7.8.2d | LoadBearing balken | Balken hebben LoadBearing property (Pset_BeamCommon) |

**Model Kwaliteit & Inventaris (3 specs)**

| Code | Specificatie | Wat wordt gecontroleerd |
|------|-------------|------------------------|
| 2.1.4 | Vermijd IfcBuildingElementProxy | Geen proxy-elementen; gebruik correcte IFC-entiteiten |
| 2.2.7.11 | Meubilair | IfcFurnishingElement met Name en NL-SfB classificatie |

#### Technische Details

- **IFC Versies:** IFC2X3 en IFC4
- **Aantal specificaties:** 27 checks
- **Bron:** Gebaseerd op [RVB BIM Norm v1.1](https://www.rijksvastgoedbedrijf.nl/) van het Rijksvastgoedbedrijf
- **PropertySets:** Pset_WallCommon, Pset_SlabCommon, Pset_DoorCommon, Pset_BeamCommon, Pset_ColumnCommon, Pset_BuildingCommon, Pset_SpaceCommon, Qto_SpaceBaseQuantities

#### Wanneer Gebruiken?

Gebruik `--ids rvb` voor:
- Projecten voor het Rijksvastgoedbedrijf (ministeries, gerechtsgebouwen, etc.)
- Rijkshuisvestingsprojecten
- Overheidsgebouwen met RVB-opdrachtgeverschap
- Projecten waar uitgebreide locatie- en gebouwinformatie vereist is
- BIM-modellen die aan RVB-inlevervoorwaarden moeten voldoen

#### Vergelijking met NL_BIM Basis ILS

| Aspect | NL_BIM Basis ILS | RVB BIM Norm |
|--------|------------------|--------------|
| Aantal checks | 12 | 27 |
| Project/terrein info | Beperkt | Uitgebreid (coördinaten, RVB-nummer) |
| NL-SfB classificatie | Algemeen | Per elementtype specifiek |
| Constructieve props | Wanden alleen | Wanden, vloeren, kolommen, balken |
| Brandtechnisch | FireRating wanden | FireRating + SelfClosing + FireExit |
| Ruimte hoeveelheden | NetFloorArea | NetFloorArea + GrossFloorArea + Height |
| Doelgroep | Algemeen bouwprojecten | Rijksvastgoed/overheid |

### Welke Standaard Kiezen?

| Situatie | Aanbevolen Standaard |
|----------|---------------------|
| Algemeen BIM-project in Nederland | `--ids nl-bim` |
| Rijksvastgoedbedrijf / overheidsgebouwen | `--ids rvb` |
| Eigen projectspecificaties | `--ids pad/naar/eigen.ids` |
| Beide standaarden tegelijk controleren | Voer beide commands uit |

---

## Praktische CLI Voorbeelden

Deze sectie bevat copy-paste ready voorbeelden voor veelvoorkomende validatietaken. Alle voorbeelden werken direct na installatie.

### Basisgebruik

```bash
# Valideer met NL_BIM Basis ILS (standaard console output)
python -m ifc_validator.cli validate mijn_model.ifc --ids nl-bim

# Valideer met RVB BIM Norm
python -m ifc_validator.cli validate mijn_model.ifc --ids rvb

# Korte optie (-i in plaats van --ids)
python -m ifc_validator.cli validate mijn_model.ifc -i nl-bim
```

### Output Formaten

```bash
# Console output (standaard, voor snelle review)
python -m ifc_validator.cli validate project.ifc --ids nl-bim --output console

# JSON output (voor automatische verwerking)
python -m ifc_validator.cli validate project.ifc --ids nl-bim --output json

# HTML rapport (voor delen met projectteam)
python -m ifc_validator.cli validate project.ifc --ids nl-bim --output html

# HTML rapport met aangepaste bestandsnaam
python -m ifc_validator.cli validate project.ifc --ids rvb --output html --html-output validatie_rapport.html
```

### Validatie Workflows

**Scenario 1: Snelle check voor oplevering**
```bash
# Controleer of model voldoet aan NL_BIM basis eisen
python -m ifc_validator.cli validate oplevering_model.ifc --ids nl-bim
```

**Scenario 2: RVB-project validatie met rapport**
```bash
# Genereer officieel validatierapport voor RVB-oplevering
python -m ifc_validator.cli validate rvb_project_v2.ifc --ids rvb --output html --html-output RVB_Validatie_Rapport.html
```

**Scenario 3: Beide standaarden vergelijken**
```bash
# Valideer tegen beide Nederlandse standaarden
python -m ifc_validator.cli validate gebouw.ifc --ids nl-bim --output json > nl_bim_resultaat.json
python -m ifc_validator.cli validate gebouw.ifc --ids rvb --output json > rvb_resultaat.json
```

**Scenario 4: Meerdere modellen valideren (Windows PowerShell)**
```powershell
# Valideer alle IFC bestanden in een folder
Get-ChildItem -Filter "*.ifc" | ForEach-Object {
    Write-Host "Validating: $($_.Name)"
    python -m ifc_validator.cli validate $_.FullName --ids nl-bim --output html
}
```

**Scenario 5: Meerdere modellen valideren (Linux/Mac Bash)**
```bash
# Valideer alle IFC bestanden in een folder
for file in *.ifc; do
    echo "Validating: $file"
    python -m ifc_validator.cli validate "$file" --ids nl-bim --output html
done
```

### Werken met Eigen IDS Bestanden

```bash
# Gebruik een eigen/aangepast IDS bestand (backward compatible)
python -m ifc_validator.cli validate model.ifc --ids mijn_specificaties.ids

# Relatief pad naar IDS bestand
python -m ifc_validator.cli validate model.ifc --ids specificaties/project_ids.ids

# Absoluut pad (Windows)
python -m ifc_validator.cli validate model.ifc --ids "C:\Projecten\IDS\custom.ids"

# Absoluut pad (Linux/Mac)
python -m ifc_validator.cli validate model.ifc --ids /home/user/ids/custom.ids
```

### Exit Codes voor Scripts

De CLI retourneert exit codes die gebruikt kunnen worden in scripts:

| Exit Code | Betekenis |
|-----------|-----------|
| `0` | ✅ Alle specificaties geslaagd |
| `1` | ❌ Een of meer specificaties gefaald, of een fout opgetreden |

**Voorbeeld: Conditionele workflow (Windows PowerShell)**
```powershell
python -m ifc_validator.cli validate model.ifc --ids nl-bim
if ($LASTEXITCODE -eq 0) {
    Write-Host "Model voldoet aan NL_BIM standaard!"
} else {
    Write-Host "Model voldoet NIET aan NL_BIM standaard. Check het rapport."
}
```

**Voorbeeld: Conditionele workflow (Linux/Mac Bash)**
```bash
if python -m ifc_validator.cli validate model.ifc --ids nl-bim; then
    echo "Model voldoet aan NL_BIM standaard!"
else
    echo "Model voldoet NIET aan NL_BIM standaard. Check het rapport."
fi
```

### JSON Output Verwerken

```bash
# Sla JSON output op in bestand
python -m ifc_validator.cli validate model.ifc --ids nl-bim --output json > validatie.json

# Bekijk alleen failed specs met jq (Linux/Mac)
python -m ifc_validator.cli validate model.ifc --ids nl-bim --output json | jq '.specifications[] | select(.status == "FAIL")'

# Bekijk alleen failed specs met PowerShell (Windows)
python -m ifc_validator.cli validate model.ifc --ids nl-bim --output json | ConvertFrom-Json | Select-Object -ExpandProperty specifications | Where-Object { $_.status -eq "FAIL" }
```

### Foutafhandeling

```bash
# Onbekende shortcut - toont beschikbare opties
python -m ifc_validator.cli validate model.ifc --ids unknown
# Output: Error: Unknown shortcut 'unknown'. Valid shortcuts are: nl-bim, rvb

# Bestand niet gevonden
python -m ifc_validator.cli validate niet_bestaand.ifc --ids nl-bim
# Output: Error: IFC file not found: niet_bestaand.ifc

# Versie tonen
python -m ifc_validator.cli validate --version
```

### Voorbeeldcommando's voor Specifieke Projecttypen

**Woningbouw:**
```bash
python -m ifc_validator.cli validate woningen_blok_a.ifc --ids nl-bim --output html --html-output Woningbouw_Validatie.html
```

**Rijkshuisvesting (ministeries, rechtbanken):**
```bash
python -m ifc_validator.cli validate ministerie_nieuwbouw.ifc --ids rvb --output html --html-output RVB_Oplevering_Rapport.html
```

**Utiliteitsbouw:**
```bash
python -m ifc_validator.cli validate kantoorgebouw.ifc --ids nl-bim --output json > kantoor_validatie.json
```

**Renovatieproject:**
```bash
# Controleer renovatiestatus van MEP-elementen (NL_BIM 4.8)
python -m ifc_validator.cli validate renovatie_project.ifc --ids nl-bim
```

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
