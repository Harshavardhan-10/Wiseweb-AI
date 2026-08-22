# Starts the Wiseweb-AI dev stack: backend API (:8000), demo site (:8001), Vite frontend (:5173).
# Safe to re-run: already-running services are left alone.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$VenvPython = Join-Path $Root "venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: venv not found at $VenvPython" -ForegroundColor Red
    exit 1
}

function PortListening([int]$port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

# 1) Backend API
if (PortListening 8000) {
    Write-Host "[8000] backend API already running" -ForegroundColor Green
}
else {
    Write-Host "[8000] starting backend API (uvicorn)..." -ForegroundColor Yellow
    $env:DATABASE_URL = "sqlite:///./local.db"
    $env:CELERY_TASK_ALWAYS_EAGER = "true"
    $env:ALLOW_LOCALHOST_SCANS = "true"   # dev-only: lets the UI scan the local demo site (:8001)
    $outLog = Join-Path $Backend "uvicorn.log"
    $errLog = Join-Path $Backend "uvicorn.err.log"
    Start-Process $VenvPython -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $Backend -RedirectStandardOutput $outLog -RedirectStandardError $errLog -WindowStyle Hidden
}

# 2) Demo site
if (PortListening 8001) {
    Write-Host "[8001] demo site already running" -ForegroundColor Green
}
else {
    Write-Host "[8001] starting demo site..." -ForegroundColor Yellow
    Start-Process $VenvPython -ArgumentList "-m", "scripts.serve_demo" -WorkingDirectory $Backend -WindowStyle Hidden
}

# 3) Frontend
if (PortListening 5173) {
    Write-Host "[5173] frontend already running" -ForegroundColor Green
}
else {
    if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        Push-Location $Frontend
        try { npm install } finally { Pop-Location }
    }
    Write-Host "[5173] starting frontend (Vite)..." -ForegroundColor Yellow
    Start-Process npm.cmd -ArgumentList "run", "dev" -WorkingDirectory $Frontend -WindowStyle Hidden
}

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "Wiseweb-AI is ready:" -ForegroundColor Cyan
Write-Host "  App:      http://localhost:5173"
Write-Host "  Login:    demo@wiseweb-ai.local / demopass123"
Write-Host "  Backend:  http://127.0.0.1:8000 (logs: backend/uvicorn.log)"
