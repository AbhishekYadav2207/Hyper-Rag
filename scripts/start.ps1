# PowerShell startup script for Hyper-RAG
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "            Starting Hyper-RAG WebUI               " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "[INFO] .env not found. Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[IMPORTANT] Created .env with default placeholders." -ForegroundColor Green
    Write-Host "Please edit .env to insert your OPENROUTER_API_KEY and MISTRAL_API_KEY." -ForegroundColor Yellow
}

# 2. Check for frontend build
if (-not (Test-Path "web-ui\frontend\dist\index.html")) {
    Write-Host "[INFO] Frontend build not detected in web-ui\frontend\dist." -ForegroundColor Yellow
    Write-Host "Attempting to build frontend with npm..." -ForegroundColor Cyan
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Push-Location "web-ui\frontend"
        try {
            npm install --no-audit --no-fund
            npm run build
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "[WARNING] npm not found in PATH." -ForegroundColor Yellow
        Write-Host "Backend will start, but WebUI static assets may not be available until you build frontend." -ForegroundColor Yellow
    }
}

# 3. Start FastAPI Uvicorn Server
Write-Host "`n[INFO] Starting Hyper-RAG server at http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server.`n" -ForegroundColor Gray

python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000
