"""HEARTBEAT MONITOR - Fixed with correct runner count."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from runner_detection import get_runner_count

def check_heartbeat():
    now = datetime.now(timezone.utc)
    runner_count = get_runner_count()
    
    issues = []
    status = "HEALTHY"
    
    if runner_count == 0:
        issues.append("NO RUNNER RUNNING")
        status = "CRITICAL"
    elif runner_count > 1:
        issues.append(f"{runner_count} runners (expected 1)")
        status = "WARNING"
    
    runner_log = Path("research/paper/V4_CANONICAL_1.0/runner_log.jsonl")
    last_heartbeat = None
    if runner_log.exists():
        with open(runner_log) as f:
            for line in f:
                if line.strip():
                    last_heartbeat = json.loads(line)
    
    if last_heartbeat:
        hb_time = datetime.fromisoformat(last_heartbeat["timestamp_utc"])
        minutes_since = (now - hb_time).total_seconds() / 60
        if minutes_since > 90:
            issues.append(f"No heartbeat in {minutes_since:.0f} min")
            status = "CRITICAL"
    
    print("="*70)
    print("  PAPER RUNNER HEARTBEAT MONITOR (FIXED)")
    print("="*70)
    print(f"\n  Status: {status}")
    print(f"  Runner count: {runner_count} (parent only)")
    print(f"  Last heartbeat: {last_heartbeat['timestamp_utc'] if last_heartbeat else 'NEVER'}")
    
    if issues:
        print(f"\n  Issues:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print(f"\n  No issues. Runner healthy.")
    
    print("="*70)

if __name__ == "__main__":
    check_heartbeat()
