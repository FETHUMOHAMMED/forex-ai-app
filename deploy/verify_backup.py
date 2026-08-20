"""Verify database backup integrity"""
import sqlite3
import sys
from pathlib import Path

def verify_backup(backup_path: str) -> bool:
    """Check if backup is valid and has expected data"""
    try:
        conn = sqlite3.connect(backup_path)
        c = conn.cursor()
        
        # Verify table structure
        c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='trades'")
        has_trades = c.fetchone()[0] > 0
        
        # Verify data integrity
        c.execute("SELECT COUNT(*) FROM trades")
        trade_count = c.fetchone()[0]
        
        c.execute("PRAGMA integrity_check")
        integrity = c.fetchone()[0]
        
        conn.close()
        
        print(f"Backup: {backup_path}")
        print(f"  Tables: {'OK' if has_trades else 'MISSING trades table'}")
        print(f"  Records: {trade_count}")
        print(f"  Integrity: {integrity}")
        
        return has_trades and integrity == 'ok'
    except Exception as e:
        print(f"Backup verification failed: {e}")
        return False

if __name__ == "__main__":
    backups = list(Path("deploy/backups").glob("trades_*.db"))
    if not backups:
        print("No backups found")
        sys.exit(1)
    
    latest = max(backups, key=lambda p: p.stat().st_mtime)
    if verify_backup(str(latest)):
        print("\nBackup VERIFIED")
    else:
        print("\nBackup FAILED verification")
        sys.exit(1)
