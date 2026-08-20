"""Fix indentation error in ai_service_daemon.py heartbeat injection"""
import sys
from pathlib import Path

daemon_path = Path("ai-service/ai_service_daemon.py")

with open(daemon_path, 'r') as f:
    content = f.read()

lines = content.split('\n')

# Find and fix the problematic heartbeat block
fixed_lines = []
skip_until_safe = False

for i, line in enumerate(lines):
    # Check if this is the problematic heartbeat block
    if 'import sys as _sys' in line and i > 0:
        prev_line = lines[i-1].strip()
        # If previous line is a function def, this needs to be indented or moved
        if prev_line.startswith('def ') or prev_line.endswith(':'):
            # This heartbeat block is incorrectly placed after a function
            # Remove it - it should be at module level
            print(f"Found misplaced heartbeat at line {i+1}")
            # Skip this block (about 10 lines)
            skip_until_safe = True
            continue
    
    if skip_until_safe:
        if line.strip() == '' or line.startswith('import ') or line.startswith('from ') or line.startswith('def '):
            skip_until_safe = False
        else:
            continue
    
    fixed_lines.append(line)

# Now add the heartbeat properly at module level
# Find the last import line
last_import = 0
for i, line in enumerate(fixed_lines):
    if line.startswith('import ') or line.startswith('from '):
        last_import = i

# Heartbeat code with proper formatting
heartbeat_block = [
    '',
    '# === Heartbeat Monitoring (Module Level) ===',
    'try:',
    '    import sys as _sys',
    '    from pathlib import Path as _Path',
    '    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))',
    '    from tools.heartbeat import Heartbeat',
    '    _heartbeat = Heartbeat("trading_daemon")',
    '    _heartbeat.start(interval_seconds=30)',
    '    print("[HEARTBEAT] Daemon heartbeat started (every 30s)")',
    'except Exception as _e:',
    '    print(f"[HEARTBEAT] Could not start heartbeat: {_e}")',
    ''
]

# Insert after last import
for line in reversed(heartbeat_block):
    fixed_lines.insert(last_import + 1, line)

content = '\n'.join(fixed_lines)

# Backup
import shutil
shutil.copy2(daemon_path, daemon_path.with_suffix('.py.bak_fix'))

with open(daemon_path, 'w') as f:
    f.write(content)

print(f"? Fixed indentation in {daemon_path}")
print("Daemon should now start without SyntaxError")
