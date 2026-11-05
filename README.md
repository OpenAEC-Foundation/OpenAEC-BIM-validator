**English** · [Nederlands](README.nl.md)

# OpenAEC BIM Validator

**Inspect IFC models in 3D, validate their information against IDS requirements, and export findings as BCF.**

[![CI](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/actions/workflows/test.yml/badge.svg)](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/actions/workflows/test.yml)
[![License](https://img.shields.io/github/license/OpenAEC-Foundation/OpenAEC-BIM-validator)](LICENSE)

[Releases](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/releases) · [Issues](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/issues)

OpenAEC BIM Validator combines a React viewer, a standalone Python validation library, a command-line tool, a FastAPI server and a Windows Tauri shell. Model validation uses IfcOpenShell and ifctester. The browser viewer displays models locally; server validation uploads the model to the configured backend.

## Try it

Python 3.11 or 3.12 and Node.js 22 are the development baseline.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]" -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd viewer
npm ci
npm run dev
```

Open the local URL printed by Vite. The production build uses `npm run build`; the Python server serves `viewer/dist` when available.

## Download

Release artifacts are listed on the [releases page](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/releases). Check the actual assets and their signing evidence before installing.

| Delivery | Scope |
|---|---|
| Windows x64 | Tauri NSIS `.exe`, with an embedded Python server, WebView2 bootstrapper and loader DLL |
| Python | Wheel and source distribution; CLI, importable validation engine and stdio MCP |
| Linux server | Container with frontend and API, non-root UID 10001, `/health` healthcheck |
| Native macOS/Linux desktop | No installer is delivered by this release workflow |
| Native product DLL/SDK | No public native ABI; consume the Python library or HTTP API |

Windows signing uses the organization's Azure signing service. The release workflow requires valid Authenticode signatures and timestamps for the application, server and installer. Missing signing access fails the workflow. Checksums and GitHub build attestations cover published assets; they do not replace Authenticode.

## Validation

```sh
ifc-validate model.ifc --ids nl-bim
ifc-validate model.ifc --ids rvb --output json
ifc-validate model.ifc --ids requirements.ids --output html --html-output report.html
```

The bundled `nl-bim` and `rvb` IDS files are project-maintained interpretations. Passing them does not establish compliance with every requirement of the source standards. Requirements outside IDS need separate assessment.

The reusable core has no dependency on the desktop shell:

```python
from ifc_validator import validate
result = validate("model.ifc", "requirements.ids")
print(result.overall_pass)
```

## Interoperability

| Format/interface | Supported use |
|---|---|
| IFC2X3 / IFC4 STEP `.ifc` | Model viewing and IDS validation |
| IDS XML `.ids` | Custom or bundled information requirements |
| JSON / HTML | CLI validation reports |
| BCF 2.1 | Import, open viewpoints, edit status and export again |
| HTTP | Upload, validation jobs, polling and BCF download |
| MCP stdio | Local validation, standards listing and report export |

## API and container

```sh
docker build -t openaec-bim-validator:local .
docker run --rm -p 127.0.0.1:8000:8000 -v bim-validator-data:/data openaec-bim-validator:local
```

API documentation: `http://127.0.0.1:8000/docs`. Submit multipart `ifc_file` and either `ids_file` or `ids_standard` to `POST /api/v1/validate`. The response is **202 Accepted** with `job_id` and `status_url`. Poll that URL for completion, then download BCF from `/api/v1/jobs/{job_id}/bcf`.

Use one server worker: jobs and uploaded-file indexes are currently held in memory. `DATABASE_URL`, `PROJECT_FILES_DIR` and `CORS_ORIGINS` configure persistent storage and browser origins. Model processing can require roughly ten times the IFC file size in RAM.

The current server is intended for local use or a controlled deployment. The separate SuperCloud API-key isolation contract is tracked in [#8](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/issues/8) and is not yet delivered.

## MCP

```json
{
  "mcpServers": {
    "ifc-validator": {
      "command": "C:/path/to/.venv/Scripts/python.exe",
      "args": ["-m", "ifc_validator.mcp_server"]
    }
  }
}
```

Tools: `validate_ifc`, `list_standards`, `export_report`. This is local stdio transport; report export writes to the requested local path. An MCP App and HTTP MCP transport are not included.

## Testing and releases

```sh
python -m pytest test tests server/tests
python scripts/version.py --check
cd viewer
npm ci
npm run check:blueprint
npm run test:run
npm run build
```

Integration tests use a temporary database. Release numbers follow **ISO year.week.sequence**, for example `2026.45.0`. Run `python scripts/version.py --next` or `--set 2026.45.1` to update all manifests and displayed versions. A matching `vYYYY.W.N` tag starts the release workflow; tests must pass before publication.

The viewer uses [OpenAEC Blueprint](https://github.com/OpenAEC-Foundation/OpenAEC-Blueprint) UI 0.4: shared React controls, native dialogs, tabs, status bar, B2 icons and local fonts. **Settings → Appearance** provides light, dark, Blueprint and two high-contrast themes. The exact source revision and compatibility changes are documented in [the Blueprint integration](docs/blueprint-ui.md).

## Open BCF files

Open **BCF → Import BCF** and select a `.bcf` or `.bcfzip` file (maximum 50 MB compressed, 100 MB expanded). Select an issue to apply its camera, component selection and visibility to the loaded model. Review comments and metadata in the detail pane, change its status, then use **Download as BCF ZIP** to save the changes.

Reimporting an existing topic ID does not overwrite local issues. Export retains topic IDs, authors, original comments, viewpoints and images. Opening cloud files uses the same import path. The local queue lasts for the current session: export changes before closing the app.

## Current limitations

- Large-model processing is memory-intensive; the API currently buffers uploaded files.
- API keys, per-key isolation, HTTP MCP, automated reruns and model revision comparison are open work.
- BCF file import supports version 2.1. The UI opens the first viewpoint; all original topic files are retained on export. External BCF API 3.0/OAuth2 status synchronization and displaying imported clipping planes remain open in #18.
- IDS editing, takeoff, measurements and classification interpretation have separate open issues.
- Signing evidence and platform support must be assessed per published release.

See the [release plan](docs/release-plan.md) and [open issues](https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator/issues).

## License

Application source: [MIT](LICENSE). IfcOpenShell, ifctester, ifcpatch and ifcclash are LGPL v3-or-later dependencies. See [third-party notices](THIRD-PARTY-NOTICES.txt); the container and Windows server bundle include a generated inventory for the installed versions.
