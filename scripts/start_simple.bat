@echo off
title Forex AI Trading System
color 0A

echo ============================================================
echo    🤖 FOREX AI TRADING SYSTEM - SIMPLE VERSION
echo ============================================================
echo.

set "ROOT=%CD%"

echo [1/2] Starting AI Service...
start "AI Service" cmd /k "cd /d "%ROOT%\ai-service" && python simple_ai.py"

timeout /t 2 /nobreak > nul

echo [2/2] Starting Backend...
start "Backend API" cmd /k "cd /d "%ROOT%\backend" && npm run dev"

echo.
echo ============================================================
echo    ✅ STARTED!
echo ============================================================
echo.
echo    📊 Frontend: http://localhost:3000
echo    🔌 API: http://localhost:3001
echo.
echo    Run this in another terminal:
echo    cd frontend ^&^& npm start
echo.
echo ============================================================
pause