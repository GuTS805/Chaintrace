<#
  ChainTrace — one-command demo launcher.

  Usage:
    .\run.ps1          Set up (if needed) and start backend + frontend, open browser.
    .\run.ps1 -Fresh   Recreate the Python venv and reinstall everything first.
    .\run.ps1 -Stop    Stop the backend (:8000) and frontend (:3000) servers.

  Offline demo path: SQLite (no Docker, no Postgres). The trained model is
  committed, so no training is needed on a fresh clone.
#>
param(
  [switch]$Fresh,
  [switch]$Stop
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPy = Join-Path $backend ".venv\Scripts\python.exe"
$venvAlembic = Join-Path $backend ".venv\Scripts\alembic.exe"
$dbUrl = "sqlite+aiosqlite:///./chaintrace.db"

function Write-Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "   $msg" -ForegroundColor DarkGray }

function Stop-Port($port) {
  $procId = (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
  if ($procId) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue; Write-Ok "stopped :$port (pid $procId)" }
}

if ($Stop) {
  Write-Step "Stopping servers"
  Stop-Port 8000
  Stop-Port 3000
  Write-Host "`nStopped." -ForegroundColor Green
  return
}

# --- locate a base Python for venv creation ---
function Find-BasePython {
  foreach ($c in @(@("py","-3.11"), @("py","-3.12"), @("py","-3.13"), @("python"))) {
    try {
      $exe = $c[0]; $arg = if ($c.Count -gt 1) { $c[1] } else { $null }
      if ($arg) { & $exe $arg --version *> $null } else { & $exe --version *> $null }
      if ($LASTEXITCODE -eq 0) { return ,$c }
    } catch { }
  }
  return $null
}

# --- backend setup ---
if ($Fresh -and (Test-Path (Join-Path $backend ".venv"))) {
  Write-Step "Removing existing venv (-Fresh)"
  Remove-Item -Recurse -Force (Join-Path $backend ".venv")
}

if (-not (Test-Path $venvPy)) {
  Write-Step "Creating Python virtual environment"
  $base = Find-BasePython
  if (-not $base) { throw "Python 3.11+ not found. Install it from python.org and retry." }
  Push-Location $backend
  if ($base.Count -gt 1) { & $base[0] $base[1] -m venv .venv } else { & $base[0] -m venv .venv }
  Write-Step "Installing backend dependencies (first run only, may take a few minutes)"
  & $venvPy -m pip install -q --upgrade pip
  & $venvPy -m pip install -q -e ".[dev]"
  Pop-Location
} else {
  Write-Ok "backend venv present"
}

$env:DATABASE_URL = $dbUrl

Write-Step "Applying database migrations (SQLite)"
Push-Location $backend
& $venvAlembic upgrade head | Out-Null

Write-Step "Seeding demo scenarios (offline)"
& $venvPy -m app.synthetic.seed | Out-Null

Write-Step "Importing real on-chain snapshots (offline replay)"
& $venvPy -m app.ingest.chain_import --file data/realchain/kraken_depositor_216b7523.json | Out-Null
& $venvPy -m app.ingest.chain_import --file data/realchain/binance_depositor_5b271663.json | Out-Null
& $venvPy -m app.ingest.chain_import --file data/realchain/tron_kraken_depositor_TVYuaXdh.json --chain tron | Out-Null

Write-Step "Building exchange deposit clusters"
& $venvPy -m app.attribution.cluster_builder | Out-Null

if (-not (Test-Path (Join-Path $backend "models\attribution_model.joblib"))) {
  Write-Step "Training attribution model (artifact missing)"
  & $venvPy -m app.attribution.train | Out-Null
} else {
  Write-Ok "model artifact present"
}
Pop-Location

# --- frontend setup ---
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
  Write-Step "Installing frontend dependencies (first run only)"
  Push-Location $frontend
  npm install --no-audit --no-fund
  Pop-Location
} else {
  Write-Ok "frontend node_modules present"
}

# --- launch servers (each in its own window) ---
Write-Step "Starting backend  -> http://localhost:8000"
Stop-Port 8000
$backCmd = "Set-Location '$backend'; `$env:DATABASE_URL='$dbUrl'; & '$venvPy' -m uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backCmd | Out-Null

Write-Step "Starting frontend -> http://localhost:3000"
Stop-Port 3000
$frontCmd = "Set-Location '$frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontCmd | Out-Null

# --- wait for backend health, then open the browser ---
Write-Step "Waiting for the API to come up"
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
    if ($r.StatusCode -eq 200) { $ready = $true; break }
  } catch { Start-Sleep -Milliseconds 750 }
}

if ($ready) {
  Start-Sleep -Seconds 3   # give Next a moment to compile the first route
  Start-Process "http://localhost:3000"
  Write-Host "`n==============================================" -ForegroundColor Green
  Write-Host "  READY" -ForegroundColor Green
  Write-Host "  Frontend : http://localhost:3000" -ForegroundColor Green
  Write-Host "  API docs : http://localhost:8000/docs" -ForegroundColor Green
  Write-Host "  Stop     : .\run.ps1 -Stop" -ForegroundColor Green
  Write-Host "==============================================`n" -ForegroundColor Green
} else {
  Write-Host "`nBackend did not respond on :8000. Check the backend window for errors." -ForegroundColor Yellow
}
