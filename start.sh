#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  AutoResearch AI — Linux/Mac Startup Script                  ║
# ║  Usage: chmod +x start.sh && ./start.sh                      ║
# ╚══════════════════════════════════════════════════════════════╝

set -e

echo ""
echo " ███████████████████████████████████████"
echo "  AutoResearch AI — Starting Services"
echo " ███████████████████████████████████████"
echo ""

# ── Activate virtual environment if present ──────────────────────────────────
if [ -f "auto/bin/activate" ]; then
    echo "[1/3] Activating virtual environment (auto/)..."
    source auto/bin/activate
elif [ -f "venv/bin/activate" ]; then
    echo "[1/3] Activating virtual environment (venv/)..."
    source venv/bin/activate
else
    echo "[1/3] No virtual environment found — using system Python."
fi

# ── Start FastAPI backend ────────────────────────────────────────────────────
echo "[2/3] Starting FastAPI backend on http://localhost:8000 ..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
echo "       PID: $API_PID"

# ── Wait briefly for API to initialise ───────────────────────────────────────
sleep 2

# ── Start Streamlit frontend ─────────────────────────────────────────────────
echo "[3/3] Starting Streamlit UI on http://localhost:8501 ..."
streamlit run app.py --server.port 8501 &
UI_PID=$!
echo "       PID: $UI_PID"

echo ""
echo " ✅  Both services started."
echo " 📡  API:      http://localhost:8000"
echo " 📚  API Docs: http://localhost:8000/docs"
echo " 🖥️   UI:       http://localhost:8501"
echo ""
echo " Press Ctrl+C to stop all services."

# ── Trap SIGINT to kill both processes ───────────────────────────────────────
trap "echo 'Stopping...'; kill $API_PID $UI_PID 2>/dev/null; exit 0" INT

wait
