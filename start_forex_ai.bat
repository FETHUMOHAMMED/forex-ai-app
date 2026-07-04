@echo off
title Forex AI System Launcher
color 0A
cd /d C:\Users\justice\forex-ai-app

:: Create logs directory
mkdir logs 2>nul

echo ============================================================
echo    🤖 FOREX AI TRADING SYSTEM - AUTO START
echo ============================================================
echo.

echo [1/5] Starting MetaTrader 5...
start "" "C:\Program Files\MetaTrader 5\terminal64.exe"
:WAIT_MT5
tasklist | find /i "terminal64.exe" >nul
if errorlevel 1 (
    timeout /t 5 /nobreak > nul
    goto WAIT_MT5
)
echo     ✅ MT5 is running

echo [2/5] Starting Backend API...
start "Forex-Backend" cmd /k "cd /d C:\Users\justice\forex-ai-app\backend && npm run dev"
echo     Waiting for backend...
:WAIT_BACKEND
timeout /t 3 /nobreak > nul
curl -s http://localhost:3001/health | findstr /C:"ok" > nul 2>&1
if errorlevel 1 goto WAIT_BACKEND
echo     ✅ Backend ready!

echo [3/5] Starting AI Signal Daemon...
start "Forex-AI-Service" cmd /k "cd /d C:\Users\justice\forex-ai-app\ai-service && .\venv\Scripts\python.exe ai_service_daemon.py"
echo     Waiting for AI service...
:WAIT_AI
timeout /t 10 /nobreak > nul
curl -s http://localhost:8001/health | findstr /C:"ready" > nul 2>&1
if errorlevel 1 goto WAIT_AI
echo     ✅ AI Service ready!

echo [4/5] Starting Watchdog...
start "Forex-Watchdog" cmd /k "cd /d C:\Users\justice\forex-ai-app\ai-service && .\venv\Scripts\python.exe watchdog.py"

echo [5/5] Starting Frontend Dashboard...
start "Forex-Frontend" cmd /k "cd /d C:\Users\justice\forex-ai-app\frontend && npm start"

echo.
echo ============================================================
echo    ✅ ALL SERVICES STARTED SUCCESSFULLY
echo ============================================================
echo.
echo    📈 MT5:        Running
echo    🔌 Backend:    http://localhost:3001
echo    🤖 AI Engine:  http://localhost:8001
echo    📊 Dashboard:  http://localhost:3000
echo    📡 WebSocket:  ws://localhost:8080
echo    🐕 Watchdog:   Running with crash protection
echo    📝 Logs:       C:\Users\justice\forex-ai-app\logs\
echo.
echo    Close this window. Other windows keep running.
echo ============================================================
echo System launcher finished. Services running in background.
exit