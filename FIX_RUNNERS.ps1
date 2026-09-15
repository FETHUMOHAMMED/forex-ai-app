# ONE-CLICK FIX: Kill all runners, start exactly ONE
Write-Host "=== FIXING RUNNERS ==="
taskkill /F /IM python.exe 2>$null
Start-Sleep 3
$remaining = (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "continuous_runner" } | Measure-Object).Count
Write-Host "After kill: $remaining runners"
if ($remaining -eq 0) {
    Write-Host "Starting ONE runner..."
    .\ai-service\venv\Scripts\python.exe -u "research\paper\V4_CANONICAL_1.0\continuous_runner.py"
}
