# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for BIM Validator CLI tool.

Bundles: ifc_validator.cli + engine + IDS standards
Output: ifc-validate.exe (console mode)
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# Project root (one level up from installer/)
ROOT = Path(SPECPATH).parent

# ---------------------------------------------------------------------------
# Collect packages with native binaries
# ---------------------------------------------------------------------------
ifcopenshell_datas, ifcopenshell_binaries, ifcopenshell_hiddenimports = collect_all("ifcopenshell")
ifctester_datas, ifctester_binaries, ifctester_hiddenimports = collect_all("ifctester")

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(ROOT / "src" / "ifc_validator" / "cli.py")],
    pathex=[str(ROOT / "src"), str(ROOT)],
    binaries=ifcopenshell_binaries + ifctester_binaries,
    datas=[
        # Bundled IDS standards
        (str(ROOT / "src" / "ifc_validator" / "standards" / "*.ids"), "ifc_validator/standards"),
        # Tray icon (reuse as CLI icon)
        (str(ROOT / "installer" / "tray_icon.ico"), "."),
    ]
    + ifcopenshell_datas
    + ifctester_datas,
    hiddenimports=[
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
        # --- CLI framework ---
        "typer",
        "typer.core",
        "typer.main",
        "click",
        "click.core",
        "rich",
        "rich.console",
        "rich.table",
        "rich.panel",
        "rich.progress",
        # --- Other ---
        "pydantic",
        "psutil",
    ]
    + ifcopenshell_hiddenimports
    + ifctester_hiddenimports,
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
        "fastapi",
        "uvicorn",
        "starlette",
        "sqlalchemy",
        "aiosqlite",
        "httpx",
        "pystray",
        "PIL",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ifc-validate",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console mode for CLI
    icon=str(ROOT / "installer" / "tray_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ifc-validate",
)
