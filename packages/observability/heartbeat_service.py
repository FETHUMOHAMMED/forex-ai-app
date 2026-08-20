"""Standalone heartbeat service - runs separately from daemon"""
import json, time, os
from pathlib import Path
from datetime import datetime, timezone

SERVICE_NAME = "trading_daemon"
INTERVAL = 30
HB_FILE = Path(f"ai-service/{SERVICE_NAME}_heartbeat.json")

print(f"[HEARTBEAT] Starting heartbeat service for {SERVICE_NAME}")
print(f"[HEARTBEAT] Writing to {HB_FILE}")
print(f"[HEARTBEAT] Interval: {INTERVAL}s")

while True:
    data = {
        "service": SERVICE_NAME,
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "status": "running"
    }
    HB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HB_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    time.sleep(INTERVAL)
