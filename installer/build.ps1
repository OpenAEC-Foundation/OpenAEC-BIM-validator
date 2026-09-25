<#
.SYNOPSIS
    Build pipeline for BIM Validator Windows installer.

.DESCRIPTION
    Orchestrates the full build: frontend → PyInstaller → Inno Setup.
    Produces a single .exe installer in installer/output/.

.PARAMETER SkipFrontend
    Skip the npm build step (use existing viewer/dist/).

.PARAMETER SkipPyInstaller
    Skip PyInstaller bundling (use existing dist/).

.PARAMETER SkipInnoSetup
    Skip Inno Setup compilation.

.EXAMPLE
    .\build.ps1
    .\build.ps1 -SkipFrontend
    .\build.ps1 -SkipPyInstaller -SkipInnoSetup
#>

param(
    [switch]$SkipFrontend,
    [switch]$SkipPyInstaller,
    [switch]$SkipInnoSetup
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$installerDir = $PSScriptRoot

Write-Host ""
Write-Host "=============================================" -ForegroundColor Magenta
Write-Host "  BIM Validator - Windows Installer Build"     -ForegroundColor Magenta
Write-Host "  3BM Bouwkunde"                               -ForegroundColor DarkMagenta
Write-Host "=============================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Project root : $root"
Write-Host "Installer dir: $installerDir"
Write-Host ""

# =========================================================================
# Step 0: Prerequisites check
# =========================================================================
Write-Host "[0/4] Checking prerequisites..." -ForegroundColor Yellow

# Node.js
if (-not $SkipFrontend) {
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) {
        throw "Node.js niet gevonden. Installeer via https://nodejs.org"
    }
    Write-Host "  Node.js: $($node.Version)" -ForegroundColor DarkGray
}

# Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python niet gevonden. Installeer Python 3.11+."
}
$pyVersion = python --version 2>&1
Write-Host "  Python : $pyVersion" -ForegroundColor DarkGray

# Inno Setup
$isccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $null
foreach ($p in $isccPaths) {
    if (Test-Path $p) { $iscc = $p; break }
}
if (-not $SkipInnoSetup -and -not $iscc) {
    throw "Inno Setup 6 niet gevonden. Download via https://jrsoftware.org/isinfo.php"
}
if ($iscc) {
    Write-Host "  ISCC   : $iscc" -ForegroundColor DarkGray
}

Write-Host "  Alle prerequisites OK" -ForegroundColor Green
Write-Host ""

# =========================================================================
# Step 1: Build React frontend
# =========================================================================
if (-not $SkipFrontend) {
    Write-Host "[1/4] Building React frontend..." -ForegroundColor Yellow

    Push-Location "$root\viewer"
    try {
        Write-Host "  npm ci..." -ForegroundColor DarkGray
        npm ci --silent 2>&1 | Out-Null

        Write-Host "  npm run build..." -ForegroundColor DarkGray
        npm run build 2>&1 | Out-Null

        if (-not (Test-Path "$root\viewer\dist\index.html")) {
            throw "Frontend build mislukt - geen dist/index.html gevonden"
        }
        Write-Host "  Frontend build OK" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "[1/4] Frontend build overgeslagen." -ForegroundColor DarkGray
    if (-not (Test-Path "$root\viewer\dist\index.html")) {
        Write-Warning "viewer/dist/index.html niet gevonden! Run zonder -SkipFrontend."
    }
}
Write-Host ""

# =========================================================================
# Step 2: Install Python build dependencies
# =========================================================================
Write-Host "[2/4] Installing Python dependencies..." -ForegroundColor Yellow

Write-Host "  pip install build dependencies..." -ForegroundColor DarkGray
python -m pip install --upgrade pip --quiet 2>&1 | Out-Null
python -m pip install -r "$installerDir\requirements-build.txt" --quiet 2>&1 | Out-Null

Write-Host "  pip install server requirements..." -ForegroundColor DarkGray
python -m pip install -r "$root\server\requirements.txt" --quiet 2>&1 | Out-Null

Write-Host "  pip install ifc-validator package..." -ForegroundColor DarkGray
python -m pip install -e "$root" --quiet 2>&1 | Out-Null

Write-Host "  Dependencies OK" -ForegroundColor Green
Write-Host ""

# =========================================================================
# Step 3: PyInstaller bundles
# =========================================================================
if (-not $SkipPyInstaller) {
    Write-Host "[3/4] Building PyInstaller bundles..." -ForegroundColor Yellow

    # Clean previous builds
    $distDir = "$installerDir\dist"
    $buildDir = "$installerDir\build"
    if (Test-Path $distDir) { Remove-Item $distDir -Recurse -Force }
    if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }

    # Build server (tray app) — windowed mode
    Write-Host "  Building server tray app..." -ForegroundColor DarkGray
    Push-Location $installerDir
    try {
        pyinstaller pyinstaller_server.spec `
            --distpath "$distDir" `
            --workpath "$buildDir\server" `
            --noconfirm 2>&1 | ForEach-Object {
                if ($_ -match "error|ERROR|Error") { Write-Host "    $_" -ForegroundColor Red }
            }

        if (-not (Test-Path "$distDir\BIMValidator\BIMValidator.exe")) {
            throw "PyInstaller server build mislukt"
        }
        Write-Host "  Server build OK: dist\BIMValidator\BIMValidator.exe" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }

    # Build CLI — console mode
    Write-Host "  Building CLI tool..." -ForegroundColor DarkGray
    Push-Location $installerDir
    try {
        pyinstaller pyinstaller_cli.spec `
            --distpath "$distDir" `
            --workpath "$buildDir\cli" `
            --noconfirm 2>&1 | ForEach-Object {
                if ($_ -match "error|ERROR|Error") { Write-Host "    $_" -ForegroundColor Red }
            }

        if (-not (Test-Path "$distDir\ifc-validate\ifc-validate.exe")) {
            throw "PyInstaller CLI build mislukt"
        }
        Write-Host "  CLI build OK: dist\ifc-validate\ifc-validate.exe" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "[3/4] PyInstaller builds overgeslagen." -ForegroundColor DarkGray
}
Write-Host ""

# =========================================================================
# Step 4: Inno Setup
# =========================================================================
if (-not $SkipInnoSetup) {
    Write-Host "[4/4] Building Inno Setup installer..." -ForegroundColor Yellow

    # Create output dir
    $outputDir = "$installerDir\output"
    if (-not (Test-Path $outputDir)) { New-Item $outputDir -ItemType Directory | Out-Null }

    & $iscc "$installerDir\bim_validator.iss"

    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compilatie mislukt (exit code: $LASTEXITCODE)"
    }

    $installer = Get-ChildItem "$outputDir\*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $sizeMB = [math]::Round($installer.Length / 1MB, 1)

    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host "  BUILD GESLAAGD!" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Installer : $($installer.FullName)" -ForegroundColor Cyan
    Write-Host "  Grootte   : $sizeMB MB" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "[4/4] Inno Setup overgeslagen." -ForegroundColor DarkGray
}

Write-Host "Build pipeline afgerond." -ForegroundColor Magenta
