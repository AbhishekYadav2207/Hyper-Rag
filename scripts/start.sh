#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "==================================================="
echo "            Starting Hyper-RAG WebUI               "
echo "==================================================="

# 1. Check for .env file
if [ ! -f ".env" ]; then
    echo "[INFO] .env not found. Creating from .env.example..."
    cp .env.example .env
    echo "[IMPORTANT] Created .env with default placeholders."
    echo "Please edit .env to insert your OPENROUTER_API_KEY and MISTRAL_API_KEY."
fi

# 2. Check for frontend build
if [ ! -f "web-ui/frontend/dist/index.html" ]; then
    echo "[INFO] Frontend build not detected in web-ui/frontend/dist."
    echo "Attempting to build frontend with npm..."
    if command -v npm &> /dev/null; then
        (cd web-ui/frontend && npm install --no-audit --no-fund && npm run build)
    else
        echo "[WARNING] npm not found in PATH."
        echo "Backend will start, but WebUI static assets may not be available until you build frontend."
    fi
fi

# 3. Start FastAPI Uvicorn Server
echo ""
echo "[INFO] Starting Hyper-RAG server at http://127.0.0.1:8000 ..."
echo "Press Ctrl+C to stop the server."
echo ""

python3 -m uvicorn web-ui.backend.main:app --host 127.0.0.1 --port 8000
