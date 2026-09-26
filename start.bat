@echo off
title Indian Railways AI ETA Prototype Launcher
echo =====================================================================
echo    Indian Railways AI ETA Intelligence Prototype (SIH26028)
echo =====================================================================
echo.

echo [1/2] Starting Backend Server (FastAPI on http://127.0.0.1:8000)...
start "Railway ETA Backend" cmd /k "cd /d "%~dp0" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

echo [2/2] Starting Frontend Server (Vite React on http://localhost:5173)...
start "Railway ETA Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Both services are now running in separate terminal windows.
echo Frontend URL: http://localhost:5173
echo Backend Docs: http://127.0.0.1:8000/docs
echo.
timeout /t 3 >nul
start http://localhost:5173
