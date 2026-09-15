"""DAILY HEALTH CHECK - Read-only experiment status."""
import subprocess
import json
from datetime import datetime, timezone
from pathlib import Path

def run_command(command: list) -> str:
    """Run a command and return output."""
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip()

def daily_health_check():
    """Run complete read-only health check."""
    print("="*70)
    print("  DAILY EXPERIMENT HEALTH CHECK (READ-ONLY)")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*70)
    
    # 1. Runner instances
    runner_check = run_command([
        "powershell", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'continuous_runner' } | Measure-Object | Select-Object -ExpandProperty Count"
    ])
    runner_count = int(runner_check.strip()) if runner_check.strip().isdigit() else 0
    
    print(f"\n  RUNNER:")
    print(f"    Instances: {runner_count}")
    if runner_count == 1:
        print(f"    Status: OK ?")
    elif runner_count == 0:
        print(f"    Status: OFFLINE ? (need to restart)")
    else:
        print(f"    Status: DUPLICATES ? (kill extras)")
    
    # 2. Live trading lock
    lock_file = Path("research/paper/V4_CANONICAL_1.0/LIVE_TRADING_LOCK.md")
    print(f"\n  LIVE TRADING:")
    print(f"    Locked: {lock_file.exists()}")
    
    # 3. Strategy frozen
    frozen_file = Path("research/paper/V4_CANONICAL_1.0/FROZEN_STRATEGY_DEFINITION.json")
    print(f"\n  STRATEGY:")
    print(f"    Frozen: {frozen_file.exists()}")
    
    # 4. Signal log status
    signal_log = Path("research/paper/V4_CANONICAL_1.0/signal_log.jsonl")
    if signal_log.exists():
        with open(signal_log, 'r') as f:
            lines = f.readlines()
        print(f"\n  EVIDENCE:")
        print(f"    Signal log entries: {len(lines)}")
        if lines:
            last_entry = json.loads(lines[-1])
            print(f"    Last evaluation: {last_entry.get('timestamp_utc', 'N/A')}")
            print(f"    Last decision: {last_entry.get('reason', 'N/A')}")
    
    # 5. Day of experiment
    start = datetime(2026, 8, 23, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    day = (now - start).days + 1
    print(f"\n  EXPERIMENT:")
    print(f"    Day: {day} of 90")
    print(f"    Progress: {(day/90)*100:.0f}%")
    
    print(f"\n{'='*70}")
    print("  STATUS: READ-ONLY CHECK COMPLETE")
    print("="*70)

if __name__ == "__main__":
    daily_health_check()
