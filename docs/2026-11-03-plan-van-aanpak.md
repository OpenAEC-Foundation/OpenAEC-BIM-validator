# Plan van aanpak OpenAEC BIM Validator

3 november 2026

## Context

De validator (FastAPI met ifctester, React/That Open-viewer, BCF, multi-tenant, Nextcloud en projectcontainers) werkt, maar loopt achter op de markt bij geometrische regels, modelversies en rapportage (zie `docs/research/functievergelijking-2026-10.md`). Tegelijk is de engine naar Rust aan het verhuizen als **Open SuperBIM Engine** (lokale repo `~/Documenten/open-superbim-engine`, nog zonder remote), met IDS 1.0 in Rust (334/334 officiële testcases), clash en BCF-export. Doel: één route kiezen van onderzoek naar product, zodat de validator in 2027 de open, zelf te hosten **poortwachter bij modeloplevering** is voor NL-opdrachtgevers, ingenieursbureaus en aannemers.

## Belangrijkste bevindingen uit het onderzoek

- **Markt:** Solibri en BIMcollab zijn de standaard, maar duur en desktop-first. Solibri heeft sinds 2026 een WebChecker (bèta, Advanced/Premium) en een AI-assistent; dat is de directe concurrent van een browserchecker.
- **Het gat:** er bestaat geen officiële webchecker van BIM Loket of het RVB. Niemand anders levert de RVB BIM-norm kant-en-klaar mee. Wij wel, plus BIM basis ILS.
- **Waar wij voorlopen:** open source, zelf te hosten, EU-hosting, volledig in de browser, REST en CLI.
- **Waar we achterlopen** (issues):
  - IDS vooraf controleren, meerdere IDS'en, schemavalidatie, rapport als PDF/Excel (#5);
  - clash en dubbele elementen (#12), modelversies en verloop (#13), automatisch hercontroleren (#14);
  - IDS-editor (#15), meten (#16), Smart Views (#17), BCF round-trip (#18), takeoff (#19);
  - regels buiten IDS (#20), georeferentie (#21), NL-SfB toetsen (#22).
- **Vertrouwen:** gebruikers willen reproduceerbare uitkomsten met versies en hashes, en een ongeldig IDS mag nooit als "model faalt" verschijnen (Musts in #5).
- **Herbruikbaar:** IDS-testcases van buildingSMART als regressiesuite, de IDS-Audit-tool (MIT), `@thatopen/components` voor editor en Smart Views (MIT), buildingSMART/validate voor normatieve regels. Xbim alleen als kruiscontrole, vanwege AGPL.

## Besluiten (open, ter goedkeuring in deze PR)

- **Engine:** nieuw validatiewerk gaat in de Rust-engine. Deze Python-repo krijgt alleen nog fixes en de koppeling (API-contract, #10/#11), tot de Rust-API hem vervangt.
- **Regelbron:** IDS blijft de enige bron van regels. Eigen regels buiten IDS (#20, #22) krijgen een apart label.
- **Hosting:** zelf te hosten blijft eis; SuperCloud is de eerste gehoste uitrol.
- **Open punt:** gratis tier voor kleine bureaus en samenwerking met DigiGO/BIM Loket. Beslissing door het team.
- **Open punt:** remote en naam van `open-superbim-engine` op GitHub. Nog niet aangemaakt.

## Doelgroepen

1. **BIM-coördinator bij een ingenieurs- of architectenbureau:** wil voor oplevering weten of het model aan de ILS voldoet, met BCF terug naar de modelleur.
2. **Opdrachtgever of beheerder** (RVB, gemeente, woningcorporatie): wil toetsen bij ontvangst, zelf hosten, en het verloop over versies zien.
3. **Aannemer of werkvoorbereider:** wil clash en hoeveelheden uit federatiemodellen.
4. **Modelleur:** wil snel zien wat er fout is, per element, met een leesbare reden, zonder licentie.
5. **Ontwikkelaar of integrator:** wil API, CLI en MCP om validatie in eigen ketens te hangen.

## Positionering en boodschap

- **Kernzin:** "De open poortwachter voor BIM-modellen: toets IFC tegen ILS en IDS, in je eigen cloud."
- **Wat ons onderscheidt:**
  - open source en zelf te hosten, data in de EU;
  - RVB BIM-norm en BIM basis ILS kant-en-klaar, met herkomst en versie;
  - officiële IDS-engine, aantoonbaar met de testcases;
  - in de browser, zonder installatie;
  - reproduceerbaar: versies en hashes in elk resultaat.
- **Niet:** concurreren met Solibri op regelcomplexiteit. Wel de laagdrempelige check bij oplevering.

## Productstrategie

**1. Vertrouwen in de uitkomst** (#5 Must)
- Versies en hashes in elk resultaat, rapport en BCF.
- Vijf uitkomsten per specificatie, per requirement in plaats van één per specificatie.
- IDS vooraf controleren met regel en kolom.
- Officiële IDS-testcases in CI, slagingspercentage zichtbaar in de UI.

**2. Rapportage**
- Rapport als HTML/PDF, JSON en CSV/XLSX, met samenvatting per specificatie.
- BCF met componenten per viewpoint en deterministische GUID's; `bcf_export.py` en `BcfExporter.ts` samenvoegen.

**3. Viewer**
- Falende elementen per specificatie kleuren, isoleren en zoomen.
- Smart Views (#17) en meten (#16).

**4. Coördinatie**
- Clash en dubbele elementen (#12) uit de Rust-engine.
- Georeferentie bij federatie (#21).

**5. Projecten over tijd**
- Modelversies vergelijken op GUID en verloop van de naleving (#13).
- Vergelijken met de vorige run: nieuw, opgelost, ongewijzigd.
- Automatisch hercontroleren bij een nieuw model in Nextcloud (#14).

**6. IDS maken**
- IDS-editor in de browser met That Open (#15), sjablonen en regex-uitleg.

**7. Integratie**
- Gedeeld SuperCloud-contract: `/v1`, OpenAPI, MCP over HTTP (#10), API-keys (#11).
- Image per release (#8, #9), versie in jaar.week (#7).

## Buiten het product (ondersteunt de strategie)

- Contact met DigiGO/BIM Loket over een open referentiechecker voor de ILS.
- RVB benaderen met de RVB-norm-set als demo.
- BCF-importtest per release in de gangbare coördinatieprogramma's, met voorbeeldpakket.
- Prioriteiten uit #5 toetsen bij drie tot vijf echte gebruikers.

## Fasering

| Fase | Wanneer | Wat |
|---|---|---|
| 0 Snelle winst | week 1 | versies en hashes in resultaat, IDS-testcases in CI, versienummer (#7), image per release (#9) |
| 1 Vertrouwen | week 2–4 | vijf uitkomsten per requirement, IDS vooraf controleren, rapport PDF/XLSX, BCF samenvoegen |
| 2 Rust-overstap | week 3–8 | Rust-API achter het SuperCloud-contract (#10/#11), vergelijken met ifctester op echte modellen, frontend op de nieuwe API |
| 3 Coördinatie | week 6–12 | clash en dubbelen in de UI (#12), kleuren per specificatie, Smart Views, meten |
| 4 Over tijd | week 10–16 | modelversies en verloop (#13), hercontrole bij upload (#14), BCF round-trip (#18) |
| 5 Verdieping | daarna | IDS-editor (#15), takeoff (#19), regels buiten IDS (#20), NL-SfB toetsen (#22), Pyodide-proef (#3) |

## Te wijzigen bestanden

- **Deze repo:**
  - `src/ifc_validator/engine/`: versies, hashes en de vijf uitkomsten, tot de Rust-engine overneemt;
  - `src/ifc_validator/web/`: `/v1`-contract en API-keys (#10/#11);
  - `server/bcf_export.py` en `viewer/src/components/bcf/BcfExporter.ts`: samenvoegen tot één BCF-pad;
  - `viewer/`: kleuren per specificatie, Smart Views, meten;
  - `tests/`: IDS-testcases als regressiesuite.
- **`open-superbim-engine`:** `superbim-ids`, `superbim-clash`, `superbim-bcf` en `superbim-api`, volgens `docs/VERBETERPLAN.md`.

## Controle

- `pytest -v` slaagt, en de IDS-testcases draaien in CI met het slagingspercentage in de uitvoer.
- Zelfde IFC + IDS + versies geeft een byte-identiek JSON-resultaat.
- Rust en ifctester geven dezelfde uitkomst op de fixtures (`NL_BIM_Basis_ILS.ids`, `RVB_BIM_Norm_v1.1.ids`) en op een model van 10, 100 en 500 MB.
- BCF opent in minstens twee coördinatieprogramma's.
- Per doelgroep nalopen: staat de uitkomst en de reden binnen twee klikken in beeld?

## Bronnen

- Onderzoek: `docs/research/alternatieven-2026-10.md`, `docs/research/functievergelijking-2026-10.md`
- Eisen: issue #5 en de issues #12–#22
- Engine: `open-superbim-engine/docs/VERBETERPLAN.md`
