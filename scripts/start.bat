@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo             Starting Hyper-RAG WebUI
echo ===================================================

cd /d "%~dp0\.."

REM 1. Check for .env file
if not exist ".env" (
    echo [INFO] .env not found. Creating from .env.example...
    copy .env.example .env >nul
    echo [IMPORTANT] Created .env with default placeholders.
    echo Please edit .env to insert your OPENROUTER_API_KEY and MISTRAL_API_KEY.
)

REM 2. Check for frontend build
if not exist "web-ui\frontend\dist\index.html" (
    echo [INFO] Frontend build not detected in web-ui\frontend\dist.
    echo Attempting to build frontend with npm...
    where npm >nul 2>nul
    if %errorlevel% equ 0 (
        pushd web-ui\frontend
        call npm install --no-audit --no-fund
        call npm run build
        popd
    ) else (
        echo [WARNING] npm is not found in PATH.
        echo Backend will start, but WebUI static assets may not be available until you build frontend.
    )
)

REM 3. Start FastAPI Uvicorn Server
echo.
echo [INFO] Starting Hyper-RAG server at http://127.0.0.1:8000 ...
echo Press Ctrl+C to stop the server.
echo.

python -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000
