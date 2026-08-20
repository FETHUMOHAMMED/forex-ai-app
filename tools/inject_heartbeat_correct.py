"""Inject heartbeat into the ACTUAL running daemon (auto_trader_exness.py)"""
import sys
from pathlib import Path
sys.path.insert(0, '.')

target_file = Path("ai-service/auto_trader_exness.py")

if not target_file.exists():
    print(f"ERROR: {target_file} not found!")
    exit()

with open(target_file, 'r') as f:
    content = f.read()

# Check if heartbeat already exists
if 'heartbeat' in content.lower():
    print("Heartbeat code already exists in auto_trader_exness.py")
    # Force update the heartbeat
    from tools.heartbeat import quick_heartbeat
    quick_heartbeat("trading_daemon")
    print("Manual heartbeat written")
    exit()

# Find last import line
lines = content.split('\n')
last_import = 0
for i, line in enumerate(lines):
    if line.startswith('import ') or line.startswith('from '):
        last_import = i

# Heartbeat code to inject
heartbeat_code = '''
# === HEARTBEAT MONITORING (Auto-injected) ===
try:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
    from tools.heartbeat import Heartbeat
    _heartbeat = Heartbeat("trading_daemon")
    _heartbeat.start(interval_seconds=30)
    print("[HEARTBEAT] Auto-trader heartbeat started (every 30s)")
except Exception as _e:
    print(f"[HEARTBEAT] Could not start: {_e}")
'''

# Insert after last import
lines.insert(last_import + 1, heartbeat_code)
content = '\n'.join(lines)

# Backup
import shutil
shutil.copy2(target_file, target_file.with_suffix('.py.bak_hb'))

# Write
with open(target_file, 'w') as f:
    f.write(content)

print(f"? Heartbeat injected into {target_file}")
print()
print("Daemon restart required:")
print("  Stop-Process -Id 12704 -Force")
print("  Start-Process .\\ai-service\\venv\\Scripts\\python.exe -ArgumentList 'ai-service/auto_trader_exness.py'")
