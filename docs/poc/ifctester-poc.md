# POC: ifctester Validatie

**Datum:** 2025-12-30
**Status:** GESLAAGD

## Samenvatting

De ifctester library (v0.8.4) van IfcOpenShell werkt succesvol voor IDS validatie. De library kan IDS bestanden laden, IFC modellen valideren, en gedetailleerde resultaten genereren in JSON formaat.

## Test Setup

### Geïnstalleerde Packages
```
ifctester==0.8.4
ifcopenshell==0.8.4.post1
```

### Test Bestanden
- **IFC:** `test/2786_CLT_model.ifc` (IFC4X3, 153.994 elementen)
- **IDS:** `ids-bestanden/NL_BIM_Basis_ILS_v2.ids` (12 specificaties)

## Resultaten

### IDS Laden
| IDS Bestand | Status | Opmerkingen |
|-------------|--------|-------------|
| NL_BIM_Basis_ILS_v2.ids | OK | Laadt correct, 12 specs |
| RVB_BIM_Norm_v1.1.ids | FOUT | XML validatie error: `<n>` i.p.v. `<name>` |

### Validatie Resultaten

```
Total specifications: 12
Passed: 4 (33%)
Failed: 8 (67%)
```

| Specificatie | Status | Details |
|-------------|--------|---------|
| 3.3 Verdiepingsnaamgeving | FAIL | 6/6 elementen falen (naamgeving pattern) |
| 3.4 Vermijd IfcBuildingElementProxy | FAIL | 7 proxy's gevonden (prohibited) |
| 3.5 Deurnaamgeving | FAIL | 0 deuren in model |
| 3.6 NL/SfB Classificatie | FAIL | 463 elementen, geen classificatie |
| 4.1 Ruimte attributen | FAIL | 0 IfcSpaces in model |
| 4.3 LoadBearing wanden | FAIL | 58 wanden missen LoadBearing |
| 4.4 IsExternal wanden | FAIL | 58 wanden missen IsExternal |
| 4.5 Brandwerendheid | PASS | N/A (geen dragende binnenwanden) |
| 4.6 ThermalTransmittance | PASS | N/A (geen externe wanden) |
| 4.7.1 Materiaal verplicht | FAIL | 293/463 elementen zonder materiaal |
| 4.7.2 Materialen dragende wanden | PASS | N/A (geen dragende wanden) |
| 4.8 Renovatiestatus MEP | PASS | N/A (geen MEP elementen) |

## API Bevindingen

### Basis Workflow
```python
import ifctester.ids
import ifcopenshell

# 1. Laad bestanden
ifc = ifcopenshell.open("model.ifc")
ids = ifctester.ids.open("rules.ids")

# 2. Valideer
ids.validate(ifc)

# 3. Check resultaten
for spec in ids.specifications:
    print(f"{spec.name}: {'PASS' if spec.status else 'FAIL'}")
```

### JSON Reporter Output
De `ifctester.reporter.Json` class genereert zeer gedetailleerde output:

```python
import ifctester.reporter

reporter = ifctester.reporter.Json(ids)
result = reporter.report()  # Returns dict, not string!
```

Output bevat per specificatie:
- `name`, `description`, `instructions`
- `status` (bool)
- `total_applicable`, `total_pass`, `total_fail`
- `requirements[]` met:
  - `facet_type` (Attribute, Property, Material, etc.)
  - `passed_entities[]` en `failed_entities[]`
  - Per failed entity: `reason`, `element`, `global_id`, `class`

### Beschikbare Reporters
```python
ifctester.reporter.Json   # Dict output (meest bruikbaar)
ifctester.reporter.Html   # HTML rapport (returnt None in tests)
ifctester.reporter.Bcf    # BCF export
ifctester.reporter.Txt    # Plain text
ifctester.reporter.Ods    # Spreadsheet
ifctester.reporter.Console # Terminal output
```

## Performance

| Metric | Waarde |
|--------|--------|
| IFC laden | ~2 sec (154K elementen) |
| IDS laden | <100ms |
| Validatie | ~5 sec |
| Totaal | ~7 sec |

## Conclusies

### Positief
1. **Werkt out-of-the-box** - Geen complexe setup nodig
2. **Gedetailleerde resultaten** - Per element failure reasons
3. **Standaard compliance** - IDS 1.0 support
4. **BCF export** - Ingebouwde BCF reporter
5. **Goede documentatie** - IfcOpenShell docs beschikbaar

### Aandachtspunten
1. **HTML reporter** - Returnt `None`, moet uitgezocht worden
2. **RVB IDS bestand** - Heeft XML fouten, moet gefixed worden
3. **Memory** - Bij grote modellen monitoren
4. **IFC4X3 support** - Werkt, maar is nieuwer schema

### Risico's
- **Laag:** Library is actief onderhouden (v0.8.4)
- **Laag:** Goede community support
- **Medium:** RVB IDS bestand moet handmatig gefixed worden

## Aanbeveling

**GO** - ifctester is geschikt als validatie-engine voor het project.

## Volgende Stappen
1. Fix RVB_BIM_Norm IDS bestand (vervang `<n>` door `<name>`)
2. Test met grotere IFC bestanden (>100MB)
3. Onderzoek HTML reporter issue
4. Begin met engine wrapper development (Fase 1)
