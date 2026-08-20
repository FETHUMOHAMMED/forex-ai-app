"""Inject scan stats tracking into the daemon"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def inject():
    daemon_path = Path("ai-service/ai_service_daemon.py")
    
    if not daemon_path.exists():
        print(f"Daemon not found at {daemon_path}")
        return
    
    with open(daemon_path, 'r') as f:
        content = f.read()
    
    # Check if already injected
    if "scan_stats" in content.lower():
        print("Scan stats already integrated in daemon")
        return
    
    # Create the injection code
    injection = '''

# === SCAN STATS INTEGRATION ===
try:
    from tools.scan_stats import scan_stats
    SCAN_STATS_ENABLED = True
    print("[STATS] Scan statistics tracking enabled")
except Exception as e:
    SCAN_STATS_ENABLED = False
    print(f"[STATS] Could not load scan_stats: {e}")

def _record_scan_stats(pairs_scanned, signals_found, signals_passed, rejections):
    """Helper to record scan statistics"""
    if SCAN_STATS_ENABLED:
        try:
            scan_stats.record_scan(pairs_scanned, signals_found, signals_passed, rejections)
        except:
            pass

def _record_order_stats():
    """Helper to record order statistics"""
    if SCAN_STATS_ENABLED:
        try:
            scan_stats.record_order()
        except:
            pass
'''
    
    # Find the heartbeat section we added earlier and add after it
    if "from tools.heartbeat import Heartbeat" in content:
        # Add after heartbeat block
        lines = content.split('\n')
        new_lines = []
        added = False
        
        for line in lines:
            new_lines.append(line)
            if not added and 'print("[HEARTBEAT] Daemon heartbeat started")' in line:
                new_lines.append(injection)
                added = True
        
        content = '\n'.join(new_lines)
    else:
        # Add at end of imports
        lines = content.split('\n')
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import_idx = i
        
        lines.insert(last_import_idx + 1, injection)
        content = '\n'.join(lines)
    
    # Backup
    import shutil
    shutil.copy2(daemon_path, daemon_path.with_suffix('.py.bak2'))
    
    with open(daemon_path, 'w') as f:
        f.write(content)
    
    print(f"[OK] Scan stats injected into {daemon_path}")
    print("")
    print("MANUAL STEP REQUIRED:")
    print("Add these calls in your daemon's signal loop:")
    print("")
    print("  # After scanning pairs:")
    print('  _record_scan_stats(["EURUSD", "GBPUSD"], signals_found, signals_passed, rejections_dict)')
    print("")
    print("  # After placing an order:")
    print("  _record_order_stats()")
    print("")
    print("Restart daemon after making these changes.")

if __name__ == "__main__":
    inject()
