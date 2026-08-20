@echo off
echo Stopping FOREX-AI-APP services...
taskkill /FI "WINDOWTITLE eq Forex-*" /F 2>nul
echo All services stopped.

