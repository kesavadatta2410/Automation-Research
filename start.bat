@echo off
REM ╔══════════════════════════════════════════════════════════════╗
REM ║  AutoResearch AI — Windows Startup Script                    ║
REM ║  Usage: double-click start.bat  OR  run from terminal        ║
REM ╚══════════════════════════════════════════════════════════════╝

echo.
echo  ███████████████████████████████████████
echo   AutoResearch AI — Starting Services
echo  ███████████████████████████████████████
echo.

REM ── Activate virtual environment if present ──────────────────────────────────
IF EXIST "auto\Scripts\activate.bat" (
    echo [1/3] Activating virtual environment...
    call auto\Scripts\activate.bat
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    echo [1/3] Activating virtual environment...
    call venv\Scripts\activate.bat
) ELSE (
    echo [1/3] No virtual environment found — using system Python.
)

REM ── Start FastAPI backend in a new terminal ──────────────────────────────────
echo [2/3] Starting FastAPI backend on http://localhost:8000 ...
start "AutoResearch API" cmd /k "uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

REM ── Wait briefly for API to initialise ───────────────────────────────────────
timeout /t 3 /nobreak >nul

REM ── Start Streamlit frontend in a new terminal ───────────────────────────────
echo [3/3] Starting Streamlit UI on http://localhost:8501 ...
start "AutoResearch UI" cmd /k "streamlit run app.py --server.port 8501"

echo.
echo  ✅  Both services are starting.
echo  📡  API:      http://localhost:8000
echo  📚  API Docs: http://localhost:8000/docs
echo  🖥️   UI:       http://localhost:8501
echo.
pause
