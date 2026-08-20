"""Verify and fix daemon heartbeat integration"""
import sys
sys.path.insert(0, '.')
from tools.heartbeat import quick_heartbeat

# Force write a fresh heartbeat
quick_heartbeat("trading_daemon")
print("Fresh heartbeat written")

# Read it back
import json
from pathlib import Path
hb_file = Path("ai-service/daemon_heartbeat.json")
if hb_file.exists():
    with open(hb_file) as f:
        data = json.load(f)
    print(f"Heartbeat content: {data}")
    print(f"Service: {data.get('service')}")
    print(f"Last heartbeat: {data.get('last_heartbeat')}")
    print(f"PID: {data.get('pid')}")

# Check what the live monitor reads
print("\nIf live monitor shows '--' or old time, check:")
print("  1. Is the daemon running from the correct file?")
print("  2. Is the heartbeat code at module level (not inside main)?")
print("  3. Is the heartbeat file path correct?")
