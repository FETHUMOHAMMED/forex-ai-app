"""Move heartbeat to module level so it runs immediately"""
import sys
from pathlib import Path
sys.path.insert(0, '.')

daemon_path = Path("ai-service/ai_service_daemon.py")
with open(daemon_path, 'r') as f:
    content = f.read()

# Check if heartbeat is inside a function
lines = content.split('\n')
heartbeat_start = None
in_function = False

for i, line in enumerate(lines):
    if 'def ' in line and not line.strip().startswith('#'):
        in_function = True
    if 'Heartbeat' in line and 'import' not in line:
        heartbeat_start = i
        break

# Find the last import line
last_import = 0
for i, line in enumerate(lines):
    if line.startswith('import ') or line.startswith('from '):
        last_import = i

# Check if heartbeat code exists but is inside a function
if heartbeat_start and heartbeat_start > last_import + 20:
    print(f"Heartbeat code at line {heartbeat_start+1}, appears inside function")
    print("Moving to module level...")
    
    # Extract the heartbeat block
    hb_lines = []
    for i in range(heartbeat_start, min(heartbeat_start + 10, len(lines))):
        hb_lines.append(lines[i])
    
    # Remove from current location
    for i in range(heartbeat_start - 1, min(heartbeat_start + 8, len(lines))):
        if i < len(lines):
            lines[i] = ''
    
    # Add after last import
    insert_pos = last_import + 1
    hb_block = '\n'.join(hb_lines)
    lines.insert(insert_pos, '\n' + hb_block + '\n')
    
    # Write back
    content = '\n'.join(lines)
    import shutil
    shutil.copy2(daemon_path, daemon_path.with_suffix('.py.bak3'))
    
    with open(daemon_path, 'w') as f:
        f.write(content)
    
    print("Heartbeat moved to module level!")
    print("Daemon needs restart to activate:")
    print("  1. Kill PID 2352: Stop-Process -Id 2352 -Force")
    print("  2. Start daemon: .\\start_daemon.bat")
else:
    print("Heartbeat already at module level or not found")
    print(f"Last import at line {last_import+1}")
    print(f"Heartbeat at line {heartbeat_start+1 if heartbeat_start else 'NOT FOUND'}")
