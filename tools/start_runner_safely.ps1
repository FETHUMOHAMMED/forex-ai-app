# SAFE RUNNER START - Kills all existing, starts exactly ONE
Write-Host "=== SAFE RUNNER START ==="

# 1. Kill ALL existing runners
Write-Host "Killing all existing runners..."
taskkill /F /IM python.exe 2>$null
Start-Sleep 3

# 2. Verify zero
$remaining = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "continuous_runner" }
Write-Host "Remaining after kill: $($remaining.Count)"

if ($remaining.Count -eq 0) {
    # 3. Start exactly ONE
    Write-Host "Starting ONE runner..."
    .\ai-service\venv\Scripts\python.exe -u "research\paper\V4_CANONICAL_1.0\continuous_runner.py"
} else {
    Write-Host "ERROR: Could not kill all runners"
}
