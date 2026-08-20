"""Continuous Scanner - Runs every 30s with graceful recovery.
HALT -> requires 3 consecutive healthy scans before READY.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
import time
from datetime import datetime, timezone
from typing import Optional

RECOVERY_THRESHOLD = 3  # Need 3 consecutive healthy scans to resume
SCAN_INTERVAL = 30       # Seconds between scans

class ContinuousScanner:
    """Runs continuous integrity checks with graceful recovery."""
    
    def __init__(self):
        self.state = "STARTING"
        self.consecutive_healthy = 0
        self.consecutive_failures = 0
        self.state_history = []
        self.recovery_required = RECOVERY_THRESHOLD
    
    def run_scan(self) -> dict:
        """Run one complete scan"""
        from packages.integrity.machine_readable import run_full_scanner
        result = run_full_scanner()
        return result
    
    def evaluate_state(self, result: dict) -> str:
        """Determine state with graceful recovery"""
        decision = result.get("overall", "HALT")
        
        if decision == "READY":
            # Check if we're in recovery mode (was HALT or RECOVERING)
            if self.state in ("HALT", "RECOVERING"):
                self.consecutive_healthy += 1
                remaining = self.recovery_required - self.consecutive_healthy
                print(f"  [RECOVERY] Healthy scan {self.consecutive_healthy}/{self.recovery_required} "
                      f"({remaining} more needed before READY)")
                if self.consecutive_healthy >= self.recovery_required:
                    self.state = "READY"
                    print(f"  [RECOVERED] {self.recovery_required} consecutive healthy scans - READY")
                else:
                    self.state = "RECOVERING"
            else:
                self.state = "READY"
                self.consecutive_healthy = self.recovery_required
            self.consecutive_failures = 0
        elif decision == "DEGRADED":
            self.state = "DEGRADED"
            self.consecutive_healthy = 0
            self.consecutive_failures = 0
        else:  # HALT
            if self.state in ("READY", "DEGRADED"):
                print(f"  [HALT] Critical failure detected!")
                print(f"  [HALT] Trading BLOCKED")
            self.state = "HALT"
            self.consecutive_healthy = 0
            self.consecutive_failures += 1
        
        return self.state
    
    def run_continuously(self):
        """Run forever with graceful recovery"""
        print("=" * 70)
        print("  CONTINUOUS SYSTEM INTEGRITY SCANNER")
        print(f"  Scan interval: {SCAN_INTERVAL}s")
        print(f"  Recovery threshold: {RECOVERY_THRESHOLD} healthy scans")
        print(f"  States: STARTING -> READY/DEGRADED/HALT -> RECOVERING -> READY")
        print("=" * 70)
        
        while True:
            try:
                result = self.run_scan()
                state = self.evaluate_state(result)
                
                icons = {
                    "READY": "[READY]",
                    "DEGRADED": "[DEGRADED]",
                    "HALT": "[HALT]",
                    "RECOVERING": "[RECOVERING]",
                    "STARTING": "[STARTING]",
                }
                icon = icons.get(state, "[?]")
                trading = "BLOCKED" if state == "HALT" else "ALLOWED" if state in ("READY", "DEGRADED") else "PENDING"
                
                print(f"\n{icon} {state} | Trading: {trading} | "
                      f"Healthy: {self.consecutive_healthy}/{RECOVERY_THRESHOLD}")
                
                # Save state
                self.save_state(result, state)
                
            except Exception as e:
                print(f"\n[SCANNER ERROR] {e}")
                self.state = "HALT"
            
            time.sleep(SCAN_INTERVAL)
    
    def save_state(self, result: dict, state: str):
        """Save scanner state for monitoring"""
        output = {
            "state": state,
            "consecutive_healthy": self.consecutive_healthy,
            "consecutive_failures": self.consecutive_failures,
            "recovery_threshold": self.recovery_required,
            "last_scan": result.get("timestamp"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        Path("ai-service/continuous_scanner_state.json").write_text(json.dumps(output, indent=2))
    
    def get_recovery_status(self) -> dict:
        """Get current recovery status"""
        return {
            "state": self.state,
            "consecutive_healthy": self.consecutive_healthy,
            "consecutive_failures": self.consecutive_failures,
            "recovery_threshold": self.recovery_required,
            "is_recovering": self.state == "RECOVERING",
            "recovered": self.state == "READY",
        }


if __name__ == "__main__":
    scanner = ContinuousScanner()
    scanner.run_continuously()
