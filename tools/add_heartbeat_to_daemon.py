"""Script to add heartbeat to the trading daemon"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

def add_heartbeat_to_daemon():
    daemon_path = Path("ai-service/ai_service_daemon.py")
    
    if not daemon_path.exists():
        print(f"Daemon not found at {daemon_path}")
        return
    
    with open(daemon_path, 'r') as f:
        content = f.read()
    
    # Check if heartbeat already added
    if "from tools.heartbeat import" in content or "Heartbeat" in content:
        print("Heartbeat already added to daemon")
        return
    
    # Add heartbeat import after existing imports
    heartbeat_import = """
# === Heartbeat Monitoring ===
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tools.heartbeat import Heartbeat

# Start heartbeat - writes every 30 seconds
_heartbeat = Heartbeat("trading_daemon")
_heartbeat.start(interval_seconds=30)
print("[HEARTBEAT] Daemon heartbeat started")
"""
    
    # Find the main() function or the main execution block
    if 'def main():' in content:
        # Add after main() definition starts
        lines = content.split('\n')
        new_lines = []
        added = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            if line.strip().startswith('def main():') and not added:
                # Add heartbeat code inside main, after any initial prints
                new_lines.append(heartbeat_import)
                added = True
        
        content = '\n'.join(new_lines)
    else:
        # Add at the top after existing imports
        # Find last import statement
        lines = content.split('\n')
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import_idx = i
        
        lines.insert(last_import_idx + 1, heartbeat_import)
        content = '\n'.join(lines)
    
    # Backup original
    import shutil
    backup_path = daemon_path.with_suffix('.py.bak')
    shutil.copy2(daemon_path, backup_path)
    print(f"Backup saved to {backup_path}")
    
    # Write updated daemon
    with open(daemon_path, 'w') as f:
        f.write(content)
    
    print(f"? Heartbeat added to {daemon_path}")
    print("  Restart daemon to activate: ./start_daemon.bat")

if __name__ == "__main__":
    add_heartbeat_to_daemon()
