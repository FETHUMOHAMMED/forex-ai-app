# FOREX-AI-APP Safe Daemon Restart
# Run this when no positions are open (Balance == Equity)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SAFE DAEMON RESTART" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check MT5 first
Write-Host "[1/5] Checking MT5 positions..." -ForegroundColor Yellow
$mt5Check = & .\ai-service\venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'.'); from tools.common import check_mt5; mt5=check_mt5(); print(f'{mt5[\"balance\"]}|{mt5[\"equity\"]}|{mt5[\"connected\"]}')"
$balance, $equity, $connected = $mt5Check.Split('|')

if ($balance -ne $equity) {
    Write-Host "  WARNING: Balance ($balance) != Equity ($equity) - Open positions detected!" -ForegroundColor Red
    Write-Host "  Restart anyway? (y/n): " -NoNewline
    $response = Read-Host
    if ($response -ne 'y') {
        Write-Host "  Aborting restart." -ForegroundColor Red
        exit
    }
} else {
    Write-Host "  No open positions - Safe to restart" -ForegroundColor Green
}

# 2. Find daemon process
Write-Host "[2/5] Finding daemon process..." -ForegroundColor Yellow
$daemon = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Id -eq 2352 -or 
    (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*ai_service_daemon*"
} | Select-Object -First 1

if ($daemon) {
    Write-Host "  Found daemon PID: $($daemon.Id)" -ForegroundColor Green
    
    # 3. Stop daemon
    Write-Host "[3/5] Stopping daemon..." -ForegroundColor Yellow
    Stop-Process -Id $daemon.Id -Force
    Start-Sleep -Seconds 2
    Write-Host "  Daemon stopped" -ForegroundColor Green
} else {
    Write-Host "  No daemon process found" -ForegroundColor Yellow
}

# 4. Start new daemon
Write-Host "[4/5] Starting daemon with all fixes..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd", "/d", "C:\Users\justice\forex-ai-app\ai-service", "&&", ".\venv\Scripts\python.exe", "ai_service_daemon.py" -WindowStyle Normal
Start-Sleep -Seconds 5

# 5. Verify
Write-Host "[5/5] Verifying..." -ForegroundColor Yellow

# Check heartbeat
Start-Sleep -Seconds 10
& .\ai-service\venv\Scripts\python.exe -c "from tools.heartbeat import quick_heartbeat; quick_heartbeat('trading_daemon')"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESTART COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Verify with:"
Write-Host "  .\ai-service\venv\Scripts\python.exe tools\diagnostics.py" -ForegroundColor White
Write-Host "  .\ai-service\venv\Scripts\python.exe tools\live_monitor.py" -ForegroundColor White
Write-Host ""
Write-Host "Start watchdog (optional):" -ForegroundColor White
Write-Host "  Start-Process .\ai-service\venv\Scripts\python.exe -ArgumentList 'tools\watchdog.py' -WindowStyle Hidden" -ForegroundColor White
