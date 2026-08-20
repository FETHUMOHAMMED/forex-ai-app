@echo off
title FOREX-AI-APP V4 SAFE LAUNCHER
color 0A
cd /d C:\Users\justice\forex-ai-app

echo ============================================================
echo    FOREX-AI-APP V4_CANONICAL_1.0
echo    PAPER TRADING ONLY - NO REAL MONEY
echo ============================================================
echo.

REM 1. Start MT5 Terminal (for data)
echo [1/2] Starting MT5 Terminal...
start "" "C:\Program Files\MetaTrader 5\terminal64.exe"
timeout /t 8 /nobreak > nul

REM 2. Start Paper Trading Runner (THE ONLY TRADING COMPONENT)
echo [2/2] Starting Paper Trading Runner...
start "V4-PaperTrader" cmd /k "cd /d C:\Users\justice\forex-ai-app && .\ai-service\venv\Scripts\python.exe -u research\paper\V4_CANONICAL_1.0\continuous_runner.py"

echo.
echo ============================================================
echo    SAFE SYSTEM STARTED
echo ============================================================
echo.
echo    1. MT5 Terminal:  Running (data only)
echo    2. Paper Trader:  V4_CANONICAL_1.0 (NO real trades)
echo.
echo    IMPORTANT:
echo    - This does NOT run auto_trader_exness.py
echo    - This does NOT open real positions
echo    - This ONLY logs paper trading signals
echo.
echo    Close THIS window only. Paper trader stays running.
echo ============================================================
timeout /t 10
exit
