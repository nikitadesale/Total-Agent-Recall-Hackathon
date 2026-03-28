#!/bin/bash
# ── Sentinel Twin — Quick Start ───────────────────────────────────────────────
# Run this from your terminal (not inside an IDE sandbox).
# Make sure you have set GMI_API_KEY and HYDRA_API_KEY in your environment
# or in a .env file.

cd "$(dirname "$0")"

# Load .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

if [ -z "$GMI_API_KEY" ]; then
  echo "⚠️  GMI_API_KEY is not set. Chat will not work."
  echo "   Copy .env.example → .env and fill in your keys."
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       SENTINEL TWIN — Starting       ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  API  → http://localhost:8000"
echo "  Docs → http://localhost:8000/docs"
echo "  UI   → http://localhost:5173"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

cd frontend && npm run dev &
UI_PID=$!

echo "Both servers started. Press Ctrl+C to stop."
wait
