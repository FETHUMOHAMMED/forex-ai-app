@echo off
title FOREX-AI-APP Launcher
color 0A
cd /d C:\Users\justice\forex-ai-app
set PYTHONIOENCODING=utf-8

echo ============================================================
echo    FOREX-AI-APP - COMPLETE SYSTEM LAUNCHER (6 SERVICES)
echo ============================================================
echo.

REM 1. Start MT5 Terminal
echo [1/6] Starting MT5 Terminal...
start "" "C:\Program Files\MetaTrader 5\terminal64.exe"
timeout /t 8 /nobreak > nul

REM 2. Start AI Signal Daemon (generates signals for auto-trader)
echo [2/6] Starting AI Signal Daemon...
start "FOREX-AI-Service" cmd /k "cd /d C:\Users\justice\forex-ai-app\ai-service && set PYTHONIOENCODING=utf-8 && .\venv\Scripts\python.exe ai_service_daemon.py"
timeout /t 10 /nobreak > nul

REM 3. Start Auto Trader (with ALL fixes)
echo [3/6] Starting Auto Trader...
start "FOREX-AutoTrader" cmd /k "cd /d C:\Users\justice\forex-ai-app\ai-service && set PYTHONIOENCODING=utf-8 && .\venv\Scripts\python.exe auto_trader_exness.py"
timeout /t 5 /nobreak > nul

REM 4. Start Backend API
echo [4/6] Starting Backend API...
start "FOREX-Backend" cmd /k "cd /d C:\Users\justice\forex-ai-app\backend && node server.js"
timeout /t 3 /nobreak > nul

REM 5. Start Watchdog
echo [5/6] Starting Watchdog...
start "FOREX-Watchdog" cmd /k "cd /d C:\Users\justice\forex-ai-app\ai-service && .\venv\Scripts\python.exe watchdog.py"
timeout /t 3 /nobreak > nul

REM 6. Start Frontend
echo [6/6] Starting Frontend Dashboard...
start "FOREX-Frontend" cmd /k "cd /d C:\Users\justice\forex-ai-app\frontend && npm start"

echo.
echo ============================================================
echo    ALL 6 SERVICES STARTED
echo ============================================================
echo.
echo    1. MT5 Terminal:     Running
echo    2. AI Signal:        http://localhost:8001
echo    3. Auto Trader:      FOREX-AutoTrader window
echo    4. Backend:          http://localhost:3001
echo    5. Watchdog:         Monitoring
echo    6. Frontend:         http://localhost:3000
echo.
echo    Close THIS window only. Other windows stay running.
echo ============================================================
timeout /t 10
exit
