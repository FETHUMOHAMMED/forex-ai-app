"""CORRECT RUNNER COUNT - Only counts parent processes."""
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

if __name__ == "__main__":
    count = get_runner_count()
    print(f"Actual runner count: {count}")
    print(f"Status: {'OK' if count == 1 else 'WARNING' if count > 1 else 'OFFLINE'}")
