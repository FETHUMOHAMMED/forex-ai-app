@echo off
echo ============================================
echo   FOREX-AI-APP - Starting All Services
echo ============================================
echo [1/5] Starting Trading Daemon...
start "Forex-TradingDaemon" cmd /c "cd ai-service && .\venv\Scripts\python.exe auto_trader_exness.py"
echo [2/5] Starting Backend API...
start "Forex-Backend" cmd /c "cd backend && node server.js"
echo [3/5] Starting Frontend...
start "Forex-Frontend" cmd /c "cd frontend && npm start"
echo [4/5] Starting Watchdog...
start "Forex-Watchdog" cmd /c ".\ai-service\venv\Scripts\python.exe packages\observability\watchdog.py"
echo [5/5] Starting Health Monitor...
start "Forex-HealthMonitor" cmd /c ".\ai-service\venv\Scripts\python.exe packages\observability\health_monitor.py"
echo All services started!
timeout /t 5


REM 6. Start V3 Dashboard API
echo [6/6] Starting V3 Dashboard API...
start "Forex-V3API" cmd /c ".\ai-service\venv\Scripts\python.exe ai-service\v3_dashboard_api.py"
