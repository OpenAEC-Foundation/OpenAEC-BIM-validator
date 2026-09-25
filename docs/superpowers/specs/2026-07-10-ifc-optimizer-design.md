# IFC Optimizer — Design

Datum: 2026-07-10 · Status: goedgekeurd (aanpak A + fasering)

## Doel

Een IFC-optimizer die modellen kleiner en schoner maakt, met selecteerbare
passes en een volledig wijzigingsrapport. Web-UI eerst; engine standalone
zodat CLI en MCP later dunne wrappers zijn (architectuurprincipe 1).

Gekozen scope (alle vier, gefaseerd):

| Fase | Inhoud |
|------|--------|
| 1 (nu) | Bestandsgrootte + model-hygiëne, web-UI met selecteerbare passes en rapport |
| 2 | Schema-conversie IFC2X3 → IFC4 (ifcpatch `Migrate`), sluit aan op de not_checkable-status |
| 3 | Geometrie-optimalisatie voor viewer-performance (apart onderzoek) |

## Veiligheidsmodel

- Altijd een **nieuw bestand**; het origineel wordt nooit aangeraakt.
- Passes zijn **individueel selecteerbaar** (zoals de IDS-standaard-keuze).
- Elke pass rapporteert wat hij deed, met GlobalIds waar van toepassing.

## Architectuur

```
src/ifc_validator/optimizer/
  __init__.py        # public API: optimize(), list_passes()
  passes.py          # pass-implementaties + registry
  models.py          # Pydantic: PassResult, OptimizeReport
server/main.py       # async job-endpoints (zelfde patroon als /api/v1/validate)
viewer/.../OptimizeDialog.tsx  # pass-checkboxes, rapport, download
```

Pass-interface: elke pass is een functie `(model: ifcopenshell.file) ->
PassResult` die het model in-place muteert (op de al geladen kopie) en
rapporteert. `optimize(input_path, passes, output_path) -> OptimizeReport`
laadt één keer, draait de geselecteerde passes in vaste volgorde, schrijft
het resultaat en meet groottes voor/na.

## Fase-1 passes

1. `fix_duplicate_globalids` — dubbele GlobalIds op IfcRoot-entiteiten
   krijgen een nieuwe GUID (eerste exemplaar behoudt de oude); rapporteert
   oud → nieuw per entiteit.
2. `remove_broken_relationships` — IfcRelationship-instanties zonder
   gerelateerde objecten (lege/null RelatedObjects e.d.) worden verwijderd.
3. `remove_unused_psets` — IfcPropertySet/IfcElementQuantity die door geen
   enkele IfcRelDefinesByProperties worden gerefereerd, verwijderen.
4. `compact` — ifcpatch-recipe `Optimise`: dedupliceert identieke
   instanties en herschrijft het bestand compact. Draait als laatste.

Volgorde ligt vast (1→4); de selectie bepaalt alleen welke meedoen.

## Web-API

Zelfde asynchrone job-patroon als validatie:

- `POST /api/v1/optimize` — multipart upload (`ifc_file`) + form-veld
  `passes` (comma-separated) → `202 {job_id}`.
- `GET /api/v1/optimize/jobs/{id}` — status + bij completed het
  `OptimizeReport` (JSON).
- `GET /api/v1/optimize/jobs/{id}/download` — het geoptimaliseerde bestand.
- Jobs verlopen via dezelfde TTL-cleanup als validatiejobs; temp-bestanden
  agressief opruimen (1GB+ modellen, 10× RAM tijdens verwerking).

## Rapport (OptimizeReport)

```json
{
  "input_file": "model.ifc",
  "size_before": 7204498, "size_after": 5100000,
  "passes": [
    {"name": "fix_duplicate_globalids", "changed": 3,
     "details": [{"entity_type": "IfcWall", "old": "…", "new": "…"}]},
    {"name": "compact", "changed": 1250, "details": []}
  ]
}
```

`details` is per pass gemaximeerd (50) met een `details_omitted`-teller —
zelfde honesty-principe als de validatierapportage.

## Viewer-UI

Knop "Optimaliseer" in de ribbon-groep MODELLEN → dialoog met: bestand-
keuze (geladen model of upload), checkbox per pass (default alle vier aan,
met omschrijving), voortgang, daarna rapport (grootte-winst + per pass de
wijzigingen) en download-knop.

## Testen

- Unit-tests per pass op synthetische fixtures (ifcopenshell in-memory:
  model met bewust dubbele GlobalIds, kapotte rel, wees-pset).
- Integratietest `optimize()` end-to-end op `test/fixtures/sample.ifc`.
- Endpoint-tests via FastAPI TestClient (upload → poll → download).

## Fouten

- Onbekende pass-naam → 422 met geldige namen.
- Corrupte IFC → job status `failed` met foutmelding (geen 500).
- `compact`-pass faalt → job faalt met de ifcpatch-fout; eerdere passes
  worden niet als resultaat aangeboden (alles-of-niets per run).
