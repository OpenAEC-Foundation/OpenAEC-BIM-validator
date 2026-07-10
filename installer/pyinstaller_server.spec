# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for BIM Validator Server (system tray app).

Bundles: tray_app.py + server/ + viewer/dist/ + IDS standards
Output: BIMValidator.exe (windowed, no console window)
"""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Project root (one level up from installer/)
ROOT = Path(SPECPATH).parent

# ---------------------------------------------------------------------------
# Collect tricky packages with native binaries / dynamic imports
# ---------------------------------------------------------------------------
ifcopenshell_datas, ifcopenshell_binaries, ifcopenshell_hiddenimports = collect_all("ifcopenshell")
ifctester_datas, ifctester_binaries, ifctester_hiddenimports = collect_all("ifctester")

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(ROOT / "installer" / "tray_app.py")],
    pathex=[str(ROOT)],
    binaries=ifcopenshell_binaries + ifctester_binaries,
    datas=[
        # Bundled frontend
        (str(ROOT / "viewer" / "dist"), "viewer/dist"),
        # Bundled IDS standards
        (str(ROOT / "src" / "ifc_validator" / "standards" / "*.ids"), "ifc_validator/standards"),
        # Server modules (not a proper package, so include as data)
        (str(ROOT / "server"), "server"),
        # Tray icon
        (str(ROOT / "installer" / "tray_icon.ico"), "."),
    ]
    + ifcopenshell_datas
    + ifctester_datas,
    hiddenimports=[
        # --- Server modules ---
        "server.main",
        "server.database",
        "server.bcf_export",
        "server.ids_validator",
        "server.ifc_processor",
        "server.job_manager",
        "server.project_manager",
        "server.nextcloud_client",
        "server.tenant_config",
        "server.volume_reader",
        "server.routers",
        "server.routers.cloud",
        "server.routers.projects",
        "server.models",
        "server.models.validation_results",
        "server.models.cloud",
        "server.models.db_models",
        # --- Core validation engine ---
        "ifc_validator",
        "ifc_validator.cli",
        "ifc_validator.engine",
        "ifc_validator.engine.parser",
        "ifc_validator.engine.validator",
        "ifc_validator.engine.file_utils",
        "ifc_validator.validator",
        "ifc_validator.formatters",
        "ifc_validator.formatters.console",
        "ifc_validator.formatters.html",
        "ifc_validator.formatters.json",
        "ifc_validator.models",
        "ifc_validator.models.results",
        "ifc_validator.standards",
        "ifc_validator.standards.resolver",
        # --- uvicorn dynamic imports ---
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        # --- FastAPI / Starlette ---
        "fastapi",
        "starlette",
        "starlette.responses",
        "starlette.staticfiles",
        "starlette.middleware",
        "starlette.middleware.cors",
        # --- Database ---
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
        "sqlalchemy.dialects.sqlite",
        "aiosqlite",
        # --- Tray app ---
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        # --- Other ---
        "multipart",
        "pydantic",
        "httpx",
        "aiofiles",
        "rich",
        "psutil",
    ]
    + ifcopenshell_hiddenimports
    + ifctester_hiddenimports
    + collect_submodules("uvicorn")
    + collect_submodules("starlette"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "notebook",
        "pytest",
        "black",
        "ruff",
        "mypy",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BIMValidator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed — no console
    disable_windowed_traceback=False,
    icon=str(ROOT / "installer" / "tray_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BIMValidator",
)
