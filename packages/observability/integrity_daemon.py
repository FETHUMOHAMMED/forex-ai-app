"""System Integrity Daemon - Runs continuously, checks ALL boundaries.
Output: READY / DEGRADED / HALT. Trading blocked on any critical failure.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import time
import json
from datetime import datetime, timezone
from packages.observability.system_integrity_gate import SystemIntegrityGate, SystemState

INTEGRITY_STATE_FILE = Path("ai-service/system_integrity_state.json")

def run_integrity_daemon(interval_seconds: int = 60):
    """Run integrity checks continuously and persist state"""
    print("[INTEGRITY DAEMON] Starting continuous system integrity monitoring")
    print(f"[INTEGRITY DAEMON] Check interval: {interval_seconds}s")
    print(f"[INTEGRITY DAEMON] States: READY / DEGRADED / HALT")
    print()
    
    gate = SystemIntegrityGate()
    
    while True:
        state = gate.run_all_checks()
        
        # Persist state
        state_data = {
            "state": state.value,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": [
                {"name": r.name, "passed": r.passed, "critical": r.critical, "detail": r.detail}
                for r in gate.results
            ],
        }
        INTEGRITY_STATE_FILE.write_text(json.dumps(state_data, indent=2))
        
        # Print state
        icons = {SystemState.READY: "[READY]", SystemState.DEGRADED: "[DEGRADED]", SystemState.HALT: "[HALT]"}
        icon = icons.get(state, "[UNKNOWN]")
        
        trading = "ALLOWED" if state != SystemState.HALT else "BLOCKED"
        print(f"{icon} {state.value} | Trading: {trading} | "
              f"{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
        
        if state == SystemState.HALT:
            critical_failures = [r for r in gate.results if not r.passed and r.critical]
            print(f"  CRITICAL FAILURES:")
            for r in critical_failures:
                print(f"    - {r.name}: {r.detail}")
        
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_integrity_daemon()
