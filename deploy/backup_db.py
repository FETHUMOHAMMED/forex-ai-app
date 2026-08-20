
"""Automated database backup with rotation"""
import shutil
from datetime import datetime, timezone
from pathlib import Path

BACKUP_DIR = Path("deploy/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def backup_database():
    src = Path("ai-service/trades.db")
    if not src.exists():
        print("No database found")
        return
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"trades_{timestamp}.db"
    shutil.copy2(src, dst)
    
    # Keep only last 20 backups
    backups = sorted(BACKUP_DIR.glob("trades_*.db"))
    while len(backups) > 20:
        backups[0].unlink()
        backups.pop(0)
    
    print(f"Backup created: {dst.name}")
    print(f"Total backups: {len(list(BACKUP_DIR.glob('trades_*.db')))}")

if __name__ == "__main__":
    backup_database()
