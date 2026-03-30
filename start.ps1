# ==============================================================
#  Subvalore - one-shot startup script (Windows / PowerShell)
#  Run from the project root: .\start.ps1
#
#  Prerequisites:
#    - Docker Desktop running
#    - Python 3.11+ installed and on PATH
#
#  First-time note:
#    If PowerShell blocks the script, run this once then retry:
#    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# ==============================================================

param (
    [switch]$SkipInstall,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Write-Step { param($msg) Write-Host "" ; Write-Host ">> $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "   OK: $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "   WARN: $msg" -ForegroundColor Yellow }
function Fail       { param($msg) Write-Host "" ; Write-Host "!! ERROR: $msg" -ForegroundColor Red ; exit 1 }

Write-Host ""
Write-Host "  =================================" -ForegroundColor Blue
Write-Host "        S U B V A L O R E          " -ForegroundColor Blue
Write-Host "    Financial Data Platform         " -ForegroundColor Blue
Write-Host "  =================================" -ForegroundColor Blue
Write-Host ""

# -- Step 1: .env --------------------------------------------------------------
Write-Step "Checking environment file"
if (-not (Test-Path "$Root\.env")) {
    Copy-Item "$Root\.env.example" "$Root\.env"
    Write-OK ".env created from .env.example (default credentials)"
} else {
    Write-OK ".env already exists"
}

# -- Step 2: Docker / PostgreSQL -----------------------------------------------
Write-Step "Starting PostgreSQL via Docker Compose"
docker compose -f "$Root\docker-compose.yml" up -d
if ($LASTEXITCODE -ne 0) { Fail "docker compose failed. Is Docker Desktop running?" }

Write-Host "   Waiting for PostgreSQL to become healthy..." -ForegroundColor DarkGray
$maxWait = 60
$elapsed = 0
do {
    Start-Sleep -Seconds 2
    $elapsed += 2
    $health = docker inspect subvalore_postgres --format "{{.State.Health.Status}}" 2>$null
} while ($health -ne "healthy" -and $elapsed -lt $maxWait)

if ($health -eq "healthy") {
    Write-OK "PostgreSQL is healthy"
} else {
    Write-Warn "Health check timed out after ${elapsed}s - continuing anyway"
}

# -- Step 3: Python virtual environment ----------------------------------------
Write-Step "Python virtual environment"
$venvPath = "$Root\backend\.venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "   Creating virtual environment..." -ForegroundColor DarkGray
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { Fail "python -m venv failed. Is Python 3.11+ on your PATH?" }
    Write-OK "Virtual environment created"
} else {
    Write-OK "Virtual environment already exists"
}

$pip     = "$venvPath\Scripts\pip.exe"
$alembic = "$venvPath\Scripts\alembic.exe"
$uvicorn = "$venvPath\Scripts\uvicorn.exe"

# -- Step 4: Install dependencies ----------------------------------------------
Write-Step "Python dependencies"
if ($SkipInstall) {
    Write-Warn "Skipping pip install (-SkipInstall flag)"
} else {
    & $pip install -r "$Root\backend\requirements.txt" --quiet
    if ($LASTEXITCODE -ne 0) { Fail "pip install failed" }
    Write-OK "Dependencies installed"
}

# -- Step 5: Database migrations -----------------------------------------------
Write-Step "Database migrations"

$migrationFiles = Get-ChildItem "$Root\migrations\versions\*.py" -ErrorAction SilentlyContinue
if (-not $migrationFiles) {
    Write-Host "   No migration files found - generating initial schema..." -ForegroundColor DarkGray
    Push-Location $Root
    & $alembic revision --autogenerate -m "initial schema"
    if ($LASTEXITCODE -ne 0) { Pop-Location ; Fail "alembic revision failed" }
    Pop-Location
}

Push-Location $Root
& $alembic upgrade head
if ($LASTEXITCODE -ne 0) { Pop-Location ; Fail "alembic upgrade head failed" }
Pop-Location
Write-OK "Migrations applied"

# -- Step 6: Open browser ------------------------------------------------------
if (-not $NoBrowser) {
    Write-Step "Opening browser"
    Start-Sleep -Seconds 1
    Start-Process "http://localhost:8000"
}

# -- Step 7: Start backend -----------------------------------------------------
Write-Step "Starting Subvalore backend"
Write-Host ""
Write-Host "  App:      http://localhost:8000" -ForegroundColor Green
Write-Host "  API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Health:   http://localhost:8000/api/health" -ForegroundColor Green
Write-Host ""
Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

Set-Location "$Root\backend"
& $uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
