[English](README.md) · **Nederlands**

# OpenAEC BIM Validator

**Bekijk IFC-modellen in 3D, toets hun informatie aan IDS-eisen en exporteer bevindingen als BCF.**

[Releases](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/releases) · [Issues](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/issues) · [MIT-licentie](LICENSE)

De validator bestaat uit een React-viewer, een zelfstandige Python-validatiebibliotheek, een CLI, een FastAPI-server en een Windows-app met Tauri. IfcOpenShell en ifctester voeren de validatie uit. De browserviewer toont modellen lokaal; servervalidatie uploadt het model naar de ingestelde backend.

## Proberen

Gebruik Python 3.11 of 3.12 en Node.js 22.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]" -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Start in een tweede terminal de viewer:

```sh
cd viewer
npm ci
npm run dev
```

Open de lokale URL die Vite toont. `npm run build` maakt de productiebuild. De Python-server serveert deze uit `viewer/dist` zodra die beschikbaar is.

## Downloaden

Controleer de bestanden en signingbewijzen op de [releasepagina](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/releases).

| Distributie | Bereik |
|---|---|
| Windows x64 | Tauri NSIS-installer, ingebouwde Python-server, WebView2-bootstrapper en loader-DLL |
| Python | Wheel en bronpakket met CLI, bibliotheek en stdio MCP |
| Linux-server | Container met viewer en API, niet-rootgebruiker 10001 en `/health` |
| Native macOS/Linux-desktop | Geen installer in deze releaseworkflow |
| Native product-DLL/SDK | Geen publieke native ABI; gebruik Python of HTTP |

Windows-signing gebruikt de Azure-signingdienst van de organisatie. De workflow vereist geldige Authenticode-signatures en tijdstempels voor app, server en installer. Ontbrekende signingtoegang laat de workflow falen. Checksums en GitHub-buildattestaties vervangen Authenticode niet.

## Valideren

```sh
ifc-validate model.ifc --ids nl-bim
ifc-validate model.ifc --ids rvb --output json
ifc-validate model.ifc --ids eisen.ids --output html --html-output rapport.html
```

De meegeleverde `nl-bim`- en `rvb`-bestanden zijn door het project onderhouden interpretaties. Een geslaagde toets bewijst geen volledige naleving van alle eisen uit de bronstandaarden. Eisen buiten IDS vragen een afzonderlijke beoordeling.

De validatiekern werkt zonder desktopinterface:

```python
from ifc_validator import validate
resultaat = validate("model.ifc", "eisen.ids")
print(resultaat.overall_pass)
```

## Uitwisseling

| Formaat/interface | Ondersteuning |
|---|---|
| IFC2X3 / IFC4 STEP `.ifc` | Tonen en valideren |
| IDS XML `.ids` | Eigen en meegeleverde eisen |
| JSON / HTML | CLI-rapporten |
| BCF 2.1 | Bevindingen en viewpoints exporteren |
| HTTP | Upload, validatiejobs, status en BCF-download |
| MCP stdio | Lokale validatie, standaarden opvragen en rapporten schrijven |

## API en container

```sh
docker build -t openaec-bim-validator:local .
docker run --rm -p 127.0.0.1:8000:8000 -v bim-validator-data:/data openaec-bim-validator:local
```

De API-documentatie staat op `http://127.0.0.1:8000/docs`. Verstuur multipart `ifc_file` met `ids_file` of `ids_standard` naar `POST /api/v1/validate`. Het antwoord is **202 Accepted**, met `job_id` en `status_url`. Vraag die status op tot de job klaar is. BCF staat vervolgens op `/api/v1/jobs/{job_id}/bcf`.

Gebruik één serverworker: jobs en uploadindexen staan in geheugen. `DATABASE_URL`, `PROJECT_FILES_DIR` en `CORS_ORIGINS` bepalen opslag en toegestane browserherkomsten. Verwerking kan ongeveer tienmaal de IFC-bestandsgrootte aan RAM vragen.

De server is bedoeld voor lokaal gebruik of een gecontroleerde deployment. Het afzonderlijke SuperCloud-contract met API-key-isolatie staat in [#8](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/issues/8) en is nog niet geleverd.

## MCP

```json
{
  "mcpServers": {
    "ifc-validator": {
      "command": "C:/pad/naar/.venv/Scripts/python.exe",
      "args": ["-m", "ifc_validator.mcp_server"]
    }
  }
}
```

Tools: `validate_ifc`, `list_standards`, `export_report`. Het transport is lokaal via stdio; rapportexport schrijft naar het opgegeven lokale pad. Een MCP App en HTTP-MCP zijn niet inbegrepen.

## Testen en releases

```sh
python -m pytest test tests server/tests
python scripts/version.py --check
cd viewer
npm ci
npm run test:run
npm run build
```

Integratietests gebruiken een tijdelijke database. Versies volgen **ISO-jaar.week.volgnummer**, bijvoorbeeld `2026.45.0`. `python scripts/version.py --next` of `--set 2026.45.1` werkt de manifests en getoonde versies bij. Een overeenkomstige tag `vYYYY.W.N` start de releaseworkflow. Tests moeten slagen vóór publicatie.

Release- en README-opbouw volgen [OpenAEC Blueprint](https://github.com/OpenAEC-Foundation/OpenAEC-Blueprint). De viewer bevat nog een eerdere OpenAEC-thema-implementatie; migratie naar de actuele gedeelde Blueprint-componenten is nog niet afgerond.

## Huidige beperkingen

- Grote modellen vragen veel RAM; de API leest uploads momenteel volledig in geheugen.
- API-keys, isolatie per key, HTTP-MCP, automatisch hertoetsen en modelversievergelijking zijn nog open werk.
- De BCF-importer is niet aangesloten op de huidige issuewachtrij in de UI.
- IDS-bewerking, hoeveelheden, meetgereedschap en classificatie-interpretatie hebben afzonderlijke issues.
- Beoordeel signingbewijs en platformondersteuning per gepubliceerde release.

Zie het [releaseplan](docs/release-plan.md) en de [open issues](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/issues).

## Licentie

Applicatiebroncode: [MIT](LICENSE). IfcOpenShell, ifctester, ifcpatch en ifcclash gebruiken LGPL v3 of later. Zie de [dependencyvermeldingen](THIRD-PARTY-NOTICES.txt). Container en Windows-serverbundel bevatten een gegenereerde inventaris van de geïnstalleerde versies.
