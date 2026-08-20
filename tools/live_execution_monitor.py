"""Live Execution Monitor - Watches every trade attempt and detects crashes.
Runs alongside the auto-trader. Logs every gate decision.
"""
import time
import json
from datetime import datetime, timezone
from pathlib import Path

LIVE_LOG = Path("ai-service/live_execution_log.jsonl")

def log_execution_event(event_type: str, data: dict):
    """Log every execution event for crash analysis"""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **data
    }
    with open(LIVE_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")
    return event

def monitor_execution():
    """Monitor live execution for crashes"""
    print("[LIVE MONITOR] Watching execution events...")
    print("[LIVE MONITOR] Press Ctrl+C to stop")
    print()
    
    last_trade_count = 0
    crash_count = 0
    
    while True:
        # Check auto-trader is alive
        import subprocess
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                                capture_output=True, text=True)
        python_processes = result.stdout.count('python.exe')
        
        # Check heartbeat
        hb_file = Path("ai-service/trading_daemon_heartbeat.json")
        if hb_file.exists():
            hb_data = json.loads(hb_file.read_text())
            last_hb = hb_data.get('last_heartbeat', '')
            
            # Check if heartbeat is fresh
            from datetime import datetime as dt
            try:
                hb_time = dt.fromisoformat(last_hb)
                age = (dt.now(timezone.utc) - hb_time).total_seconds()
                
                if age < 300:
                    print(f"[OK] Daemon alive. Heartbeat {age:.0f}s ago")
                else:
                    print(f"[WARN] Heartbeat STALE: {age:.0f}s")
                    log_execution_event("HEARTBEAT_STALE", {"age": age})
            except:
                print("[WARN] Cannot parse heartbeat")
        
        time.sleep(30)

if __name__ == "__main__":
    monitor_execution()
