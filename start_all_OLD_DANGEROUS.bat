@echo off
echo ============================================
echo   FOREX-AI-APP - Starting All Services
echo ============================================

REM Start Backend Server
echo [1/4] Starting Backend Server...
start "Backend-Server" cmd /c "cd backend && node server.js"

REM Start Backend API (if different from server)
echo [2/4] Starting Backend API...
start "Backend-API" cmd /c "cd backend && nodemon server.js"

REM Start Trading Daemon
echo [3/4] Starting Trading Daemon...
start "Trading-Daemon" cmd /c "cd ai-service && .\venv\Scripts\python.exe ai_service_daemon.py"

REM Start Watchdog
echo [4/4] Starting Watchdog...
start "Watchdog" cmd /c ".\ai-service\venv\Scripts\python.exe tools\watchdog.py"

REM Start Frontend (optional - usually started separately)
echo [Optional] Starting Frontend...
start "Frontend" cmd /c "cd frontend && npm start"

echo.
echo ============================================
echo   All services started!
echo   Run diagnostics: .\ai-service\venv\Scripts\python.exe tools\diagnostics.py
echo ============================================
timeout /t 5
