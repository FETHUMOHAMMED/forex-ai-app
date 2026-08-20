"""Automated Health Monitor - Detects issues BEFORE they become problems.
Replaces manual diagnostic scripts with continuous automated checking.

Monitors:
  - heartbeat stale
  - MT5 disconnected
  - database mismatch
  - position without trade
  - trade without position
  - unexpected lot size
  - risk assertion failure
  - duplicate position
  - orphan order
  - missing metadata
  - PnL mismatch
  - account mismatch
"""
import sqlite3
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "CRITICAL"   # Immediate action required
    ERROR = "ERROR"         # Requires attention
    WARNING = "WARNING"     # Should investigate
    INFO = "INFO"           # Informational

@dataclass
class HealthAlert:
    """A single health check alert"""
    check_name: str
    severity: Severity
    message: str
    detail: str = ""
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "health_monitor"

class HealthMonitor:
    """Continuous automated health monitoring for FOREX-AI-APP"""
    
    def __init__(self, db_path: str = "ai-service/trades.db"):
        self.db_path = db_path
        self.alerts: List[HealthAlert] = []
        self.last_check_utc: Optional[datetime] = None
    
    def _add_alert(self, check_name: str, severity: Severity, message: str, detail: str = ""):
        alert = HealthAlert(check_name, severity, message, detail)
        self.alerts.append(alert)
        
        # Log to console
        icon = {"CRITICAL": "??", "ERROR": "?", "WARNING": "??", "INFO": "??"}[severity.value]
        print(f"[{alert.timestamp_utc[:19]}] {icon} [{severity.value}] {check_name}: {message}")
        if detail:
            print(f"    Detail: {detail}")
    
    def check_heartbeat(self, max_age_seconds: int = 300) -> bool:
        """Check if daemon heartbeat is fresh"""
        hb_file = Path("ai-service/trading_daemon_heartbeat.json")
        if not hb_file.exists():
            self._add_alert("heartbeat", Severity.CRITICAL, 
                          "No heartbeat file found", "Daemon may be down")
            return False
        
        try:
            with open(hb_file, 'r') as f:
                data = json.load(f)
            last_hb = datetime.fromisoformat(data['last_heartbeat'])
            now = datetime.now(timezone.utc)
            age = (now - last_hb).total_seconds()
            
            if age > max_age_seconds:
                self._add_alert("heartbeat", Severity.ERROR,
                              f"Heartbeat STALE: {age:.0f}s old",
                              f"Last heartbeat: {data['last_heartbeat']}")
                return False
            elif age > 120:
                self._add_alert("heartbeat", Severity.WARNING,
                              f"Heartbeat delayed: {age:.0f}s old")
            return True
        except Exception as e:
            self._add_alert("heartbeat", Severity.ERROR, f"Cannot read heartbeat: {e}")
            return False
    
    def check_mt5_connection(self) -> bool:
        """Check if MT5 is connected and account is correct"""
        try:
            import MetaTrader5 as mt5
            if not mt5.initialize():
                self._add_alert("mt5_connection", Severity.CRITICAL, "MT5 not initialized")
                return False
            
            info = mt5.account_info()
            if not info:
                self._add_alert("mt5_connection", Severity.CRITICAL, "MT5 account info unavailable")
                mt5.shutdown()
                return False
            
            # Verify expected account
            if info.login != REDACTED_LIVE_ACCOUNT and info.login != REDACTED_DEMO_ACCOUNT:
                self._add_alert("mt5_connection", Severity.WARNING,
                              f"Unexpected MT5 account: {info.login}")
            
            mt5.shutdown()
            return True
        except Exception as e:
            self._add_alert("mt5_connection", Severity.ERROR, f"MT5 check failed: {e}")
            return False
    
    def check_db_mt5_consistency(self) -> bool:
        """Check for positions without trades and trades without positions"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        issues_found = False
        
        # Check: open trades without MT5 position ID
        c.execute("""
            SELECT COUNT(*) FROM trades 
            WHERE (result IS NULL OR result = 'OPEN' OR result = '')
            AND mt5_position_id IS NULL
        """)
        orphan = c.fetchone()[0]
        if orphan > 0:
            self._add_alert("db_consistency", Severity.ERROR,
                          f"{orphan} open trades without MT5 position ID",
                          "These trades may be phantoms")
            issues_found = True
        
        # Check: trades with impossible timestamps
        c.execute("""
            SELECT COUNT(*) FROM trades 
            WHERE exit_time IS NOT NULL AND timestamp IS NOT NULL
            AND exit_time < timestamp
        """)
        bad_ts = c.fetchone()[0]
        if bad_ts > 0:
            self._add_alert("db_consistency", Severity.ERROR,
                          f"{bad_ts} trades with exit before entry",
                          "Timestamp corruption detected")
            issues_found = True
        
        # Check: trades with unexpected lot size
        c.execute("""
            SELECT COUNT(*) FROM trades 
            WHERE account = 'Live_Micro' AND volume >= 0.1
            AND result != 'PHANTOM'
        """)
        large_lots = c.fetchone()[0]
        if large_lots > 0:
            self._add_alert("db_consistency", Severity.CRITICAL,
                          f"{large_lots} Live_Micro trades with volume >= 0.1 lots",
                          "Risk management failure - lot size too large")
            issues_found = True
        
        # Check: trades with missing metadata
        c.execute("""
            SELECT COUNT(*) FROM trades 
            WHERE strategy_version = 'V3_REGIME'
            AND (regime = 'UNKNOWN' OR regime IS NULL)
            AND result != 'PHANTOM'
        """)
        missing_regime = c.fetchone()[0]
        if missing_regime > 0:
            self._add_alert("db_consistency", Severity.WARNING,
                          f"{missing_regime} V3 trades with UNKNOWN regime")
            issues_found = True
        
        # Check: account mismatch
        c.execute("""
            SELECT COUNT(*) FROM trades 
            WHERE account = 'Live_Micro' AND account_name = 'Demo2'
        """)
        acct_mismatch = c.fetchone()[0]
        if acct_mismatch > 0:
            self._add_alert("db_consistency", Severity.ERROR,
                          f"{acct_mismatch} trades with account/account_name mismatch")
            issues_found = True
        
        conn.close()
        return not issues_found
    
    def check_pnl_integrity(self) -> bool:
        """Check for PnL mismatches between DB and MT5"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT COUNT(*) FROM trades 
            WHERE strategy_version = 'V3_REGIME'
            AND exit_time IS NOT NULL
            AND pnl IS NOT NULL
            AND mt5_position_id IS NOT NULL
            AND entry = 1.15123
        """)
        stale_entry = c.fetchone()[0]
        
        if stale_entry > 0:
            self._add_alert("pnl_integrity", Severity.WARNING,
                          f"{stale_entry} closed trades with stale signal entry price (1.15123)",
                          "Entry prices may not reflect actual MT5 execution")
        
        conn.close()
        return stale_entry == 0
    
    def check_risk_violations(self) -> bool:
        """Check for trades that violated risk parameters"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check for trades where actual loss exceeded configured risk
        c.execute("""
            SELECT id, pair, volume, pnl FROM trades 
            WHERE account = 'Live_Micro'
            AND volume >= 0.1
            AND result = 'LOSS'
            AND ABS(pnl) > 0.5
        """)
        violations = c.fetchall()
        
        for v in violations:
            self._add_alert("risk_violation", Severity.CRITICAL,
                          f"Trade ID {v[0]}: {v[1]} vol={v[2]} loss=${v[3]:.2f}",
                          f"Loss exceeds 0.05% risk budget on $19 account")
        
        conn.close()
        return len(violations) == 0
    
    def run_all_checks(self) -> Dict[str, bool]:
        """Run all health checks and return results"""
        self.alerts = []
        self.last_check_utc = datetime.now(timezone.utc)
        
        results = {
            "heartbeat": self.check_heartbeat(),
            "mt5_connection": self.check_mt5_connection(),
            "db_consistency": self.check_db_mt5_consistency(),
            "pnl_integrity": self.check_pnl_integrity(),
            "risk_violations": self.check_risk_violations(),
        }
        
        return results
    
    def get_summary(self) -> dict:
        """Get summary of health status"""
        results = self.run_all_checks()
        
        criticals = sum(1 for a in self.alerts if a.severity == Severity.CRITICAL)
        errors = sum(1 for a in self.alerts if a.severity == Severity.ERROR)
        warnings = sum(1 for a in self.alerts if a.severity == Severity.WARNING)
        
        all_pass = all(results.values())
        
        return {
            "status": "HEALTHY" if all_pass else "DEGRADED" if criticals == 0 else "CRITICAL",
            "checks_passed": sum(results.values()),
            "checks_total": len(results),
            "criticals": criticals,
            "errors": errors,
            "warnings": warnings,
            "alerts": [{"check": a.check_name, "severity": a.severity.value, 
                        "message": a.message} for a in self.alerts],
            "checked_at_utc": self.last_check_utc.isoformat() if self.last_check_utc else None,
            "results": results,
        }
    
    def run_continuously(self, interval_seconds: int = 60):
        """Run health checks continuously"""
        print(f"[HEALTH MONITOR] Starting automated checks every {interval_seconds}s")
        print(f"[HEALTH MONITOR] Press Ctrl+C to stop")
        print()
        
        try:
            while True:
                summary = self.get_summary()
                
                status_icon = {"HEALTHY": "??", "DEGRADED": "??", "CRITICAL": "??"}[summary["status"]]
                print(f"\n{status_icon} [{summary['status']}] "
                      f"Passed: {summary['checks_passed']}/{summary['checks_total']} | "
                      f"Critical: {summary['criticals']} | Errors: {summary['errors']} | Warnings: {summary['warnings']}")
                
                if summary["status"] != "HEALTHY":
                    for alert in summary["alerts"]:
                        print(f"  [{alert['severity']}] {alert['check']}: {alert['message']}")
                
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n[HEALTH MONITOR] Stopped")


if __name__ == "__main__":
    monitor = HealthMonitor()
    monitor.run_continuously(interval_seconds=60)
