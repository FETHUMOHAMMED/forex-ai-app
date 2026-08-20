"""Continue improvements - Phase 2 recommendations"""
import os
import json
from pathlib import Path

print("=" * 60)
print("  CONTINUING SYSTEM IMPROVEMENTS")
print("=" * 60)

# ========================================================================
# 1. Create centralized configuration
# ========================================================================
print("\n[1/6] Centralized Configuration...")
config_dir = Path("config")
config_dir.mkdir(exist_ok=True)

trading_config = {
    "risk_per_trade": 0.0005,
    "max_daily_trades": 5,
    "max_daily_loss_pct": 0.05,
    "max_open_positions": 3,
    "session_hours": {"EURUSD": [[7, 11]]},
    "signal_max_age_seconds": 120,
    "max_entry_deviation_pips": 5.0,
}
(config_dir / "trading.yaml").write_text(json.dumps(trading_config, indent=2))
print("  Created config/trading.yaml")

account_config = {
    "Live_Micro": {
        "account_id": REDACTED_LIVE_ACCOUNT,
        "server": "Exness-MT5Real10",
        "risk_percent": 0.0005,
        "environment": "LIVE_MICRO_VALIDATION",
    },
    "Demo2": {
        "account_id": REDACTED_DEMO_ACCOUNT,
        "server": "Exness-MT5Trial9",
        "risk_percent": 0.01,
        "environment": "DEMO",
    }
}
(config_dir / "accounts.yaml").write_text(json.dumps(account_config, indent=2))
print("  Created config/accounts.yaml")

# ========================================================================
# 2. Add health check endpoint
# ========================================================================
print("\n[2/6] Health Check Endpoint...")
health_file = Path("apps/api/health.py")
health_file.parent.mkdir(parents=True, exist_ok=True)
health_file.write_text('''
"""Health check endpoint for orchestration"""
from fastapi import APIRouter
from datetime import datetime, timezone
import sqlite3

router = APIRouter()

@router.get("/health")
def health_check():
    """Full system health check"""
    db_ok = False
    try:
        conn = sqlite3.connect("ai-service/trades.db")
        conn.execute("SELECT 1")
        conn.close()
        db_ok = True
    except:
        pass
    
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": db_ok,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
    }
''')
print("  Created apps/api/health.py")

# ========================================================================
# 3. Add structured logging
# ========================================================================
print("\n[3/6] Structured Logging...")
log_file = Path("packages/observability/structured_logger.py")
log_file.parent.mkdir(parents=True, exist_ok=True)
log_file.write_text('''
"""Structured JSON logging for production"""
import json
from datetime import datetime, timezone

def log_event(event_type: str, data: dict, level: str = "INFO"):
    """Log structured event as JSON"""
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event_type,
        **data
    }
    print(json.dumps(entry))
    return entry
''')
print("  Created packages/observability/structured_logger.py")

# ========================================================================
# 4. Add circuit breaker pattern
# ========================================================================
print("\n[4/6] Circuit Breaker...")
cb_file = Path("packages/execution/circuit_breaker.py")
cb_file.parent.mkdir(parents=True, exist_ok=True)
cb_file.write_text('''
"""Circuit breaker for MT5 connection failures"""
import time
from datetime import datetime, timezone
from enum import Enum

class CircuitState(str, Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Failing - block all orders
    HALF_OPEN = "HALF_OPEN" # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
        self.last_success_time = None
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def record_success(self):
        self.failure_count = 0
        self.last_success_time = datetime.now(timezone.utc)
        self.state = CircuitState.CLOSED
    
    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
            return False
        return True  # HALF_OPEN - allow one test order
    
    def reset(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
''')
print("  Created packages/execution/circuit_breaker.py")

# ========================================================================
# 5. Add backup script
# ========================================================================
print("\n[5/6] Database Backup Script...")
backup_script = Path("deploy/backup_db.py")
backup_script.write_text('''
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
''')
print("  Created deploy/backup_db.py")

# ========================================================================
# 6. Update .env template
# ========================================================================
print("\n[6/6] Update .env template...")
env_template = Path(".env.template")
env_template.write_text('''# FOREX-AI-APP Environment Variables
# Copy to .env and fill in credentials

# MT5 Accounts
MT5_PASSWORD_REDACTED_LIVE_ACCOUNT=your_live_micro_password
MT5_SERVER_REDACTED_LIVE_ACCOUNT=Exness-MT5Real10
MT5_PASSWORD_REDACTED_DEMO_ACCOUNT=your_demo2_password
MT5_SERVER_REDACTED_DEMO_ACCOUNT=Exness-MT5Trial9

# API Security
FOREX_API_KEY=your_secure_api_key_here

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Slack (optional)
SLACK_WEBHOOK_URL=

# Database
DB_PATH=ai-service/trades.db
''')
print("  Updated .env.template with API key")

print(f"\n{'='*60}")
print("  ALL IMPROVEMENTS APPLIED")
print(f"{'='*60}")
print("""
Created:
  1. config/trading.yaml - Centralized risk config
  2. config/accounts.yaml - Account definitions
  3. apps/api/health.py - Health check endpoint
  4. packages/observability/structured_logger.py - JSON logging
  5. packages/execution/circuit_breaker.py - MT5 failure protection
  6. deploy/backup_db.py - Automated backups with rotation
  7. .env.template - Updated with API key variable
""")
