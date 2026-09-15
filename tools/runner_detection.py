"""CORRECT RUNNER DETECTION - Shared by all monitoring tools."""
import subprocess

def get_runner_count():
    """Count only PARENT runners, not child processes."""
    result = subprocess.run(
        ["powershell", "-Command", 
         """
         $allRunners = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'continuous_runner' }
         $parentCount = 0
         foreach ($runner in $allRunners) {
             $procId = $runner.ProcessId
             $parentInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $procId"
             $parentId = $parentInfo.ParentProcessId
             $parentCmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $parentId" -ErrorAction SilentlyContinue).CommandLine
             if ($parentCmd -notmatch 'continuous_runner') {
                 $parentCount++
             }
         }
         Write-Output $parentCount
         """],
        capture_output=True, text=True
    )
    
    try:
        return int(result.stdout.strip())
    except:
        return 0

def get_runner_status():
    """Get runner status with correct count."""
    count = get_runner_count()
    if count == 1:
        return count, "ONLINE"
    elif count > 1:
        return count, "DUPLICATES"
    else:
        return count, "OFFLINE"
