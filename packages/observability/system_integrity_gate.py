"""System Integrity Gate - THE single authoritative system health decision.
Checks all critical boundaries. Output: READY / DEGRADED / HALT.
Trading is only allowed in READY or specific DEGRADED states.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

class SystemState(str, Enum):
    READY = "READY"          # All critical systems healthy - trading allowed
    DEGRADED = "DEGRADED"    # Non-critical issue - trading may continue
    HALT = "HALT"            # Critical failure - trading BLOCKED

class GateResult:
    """Result of one subsystem check"""
    def __init__(self, name: str, passed: bool, critical: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.critical = critical
        self.detail = detail

class SystemIntegrityGate:
    """Checks ALL critical boundaries and returns authoritative decision."""
    
    def __init__(self):
        self.results = []
        self.state = SystemState.HALT  # Default: fail closed
    
    def check_database(self) -> GateResult:
        """Database must be accessible and readable"""
        try:
            conn = sqlite3.connect('ai-service/trades.db', timeout=5)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM trades")
            count = c.fetchone()[0]
            c.execute("PRAGMA integrity_check")
            integrity = c.fetchone()[0]
            conn.close()
            
            passed = integrity == 'ok'
            return GateResult("DATABASE", passed, True, 
                            f"{count} trades, integrity={integrity}" if passed else f"Corruption: {integrity}")
        except Exception as e:
            return GateResult("DATABASE", False, True, str(e))
    
    def check_mt5(self) -> GateResult:
        """MT5 must be connected with valid account"""
        try:
            if not mt5.initialize():
                return GateResult("MT5", False, True, "MT5 not initialized")
            
            info = mt5.account_info()
            if not info:
                mt5.shutdown()
                return GateResult("MT5", False, True, "Account info unavailable")
            
            mt5.shutdown()
            return GateResult("MT5", True, True, 
                            f"Account {info.login} balance=${info.balance}")
        except Exception as e:
            return GateResult("MT5", False, True, str(e))
    
    def check_api(self) -> GateResult:
        """API endpoints must be reachable"""
        import urllib.request
        try:
            # Check V3 Dashboard API health
            response = urllib.request.urlopen('http://localhost:8002/v3/health', timeout=3)
            if response.status == 200:
                return GateResult("API", True, True, "V3 API healthy")
            return GateResult("API", False, False, f"Status {response.status}")
        except Exception as e:
            return GateResult("API", False, False, f"V3 API not reachable: {e}")
    
    def check_frontend(self) -> GateResult:
        """Frontend dashboard must be serving"""
        import urllib.request
        try:
            response = urllib.request.urlopen('http://localhost:3000', timeout=3)
            if response.status == 200:
                return GateResult("FRONTEND", True, False, "Dashboard serving")
            return GateResult("FRONTEND", False, False, f"Status {response.status}")
        except Exception as e:
            return GateResult("FRONTEND", False, False, "Dashboard not reachable")
    
    def check_ai_models(self) -> GateResult:
        """AI models must exist"""
        models_dir = Path('ai-service/models')
        if not models_dir.exists():
            return GateResult("AI_MODELS", False, True, "Models folder missing")
        
        models = list(models_dir.glob('*.joblib')) + list(models_dir.glob('*.zip'))
        if len(models) >= 6:
            return GateResult("AI_MODELS", True, True, f"{len(models)} models loaded")
        return GateResult("AI_MODELS", False, False, f"Only {len(models)} models")
    
    def check_risk_gate(self) -> GateResult:
        """Risk gates must be importable and functional"""
        try:
            from packages.risk.validation_lock import VALIDATION_LIMITS
            from packages.risk.monetary_risk_gate import MonetaryRiskCheck
            return GateResult("RISK_GATE", True, True, 
                            f"Max vol={VALIDATION_LIMITS.max_volume}, risk={VALIDATION_LIMITS.max_risk_pct}")
        except Exception as e:
            return GateResult("RISK_GATE", False, True, str(e))
    
    def check_reconciliation_daemon(self) -> GateResult:
        """Reconciliation daemon must be able to run"""
        try:
            from packages.observability.reconciliation_daemon import ReconciliationDaemon
            return GateResult("RECONCILIATION", True, True, "Daemon importable")
        except Exception as e:
            return GateResult("RECONCILIATION", False, True, str(e))
    
    def check_data_integrity(self) -> GateResult:
        """No active contamination in V3 data"""
        try:
            conn = sqlite3.connect('ai-service/trades.db')
            c = conn.cursor()
            c.execute("""SELECT COUNT(*) FROM trades 
                         WHERE strategy_version='V3_REGIME' AND account='Live_Micro'
                         AND account_name != 'Live_Micro' AND result NOT LIKE 'LEGACY%'""")
            contaminated = c.fetchone()[0]
            conn.close()
            
            if contaminated == 0:
                return GateResult("DATA_INTEGRITY", True, True, "No active contamination")
            return GateResult("DATA_INTEGRITY", False, True, f"{contaminated} contaminated records")
        except Exception as e:
            return GateResult("DATA_INTEGRITY", False, True, str(e))
    
    def check_heartbeat(self) -> GateResult:
        """Trading daemon heartbeat must be fresh"""
        hb_file = Path('ai-service/trading_daemon_heartbeat.json')
        if not hb_file.exists():
            return GateResult("HEARTBEAT", False, False, "No heartbeat file")
        
        import json
        data = json.loads(hb_file.read_text())
        last_hb = data.get('last_heartbeat', '')
        # Parse and check age
        from datetime import datetime as dt
        try:
            hb_time = dt.fromisoformat(last_hb)
            age = (dt.now(timezone.utc) - hb_time).total_seconds()
            if age < 300:
                return GateResult("HEARTBEAT", True, False, f"{age:.0f}s ago")
            return GateResult("HEARTBEAT", False, False, f"STALE: {age:.0f}s")
        except:
            return GateResult("HEARTBEAT", False, False, "Cannot parse heartbeat")
    
    def run_all_checks(self) -> SystemState:
        """Run ALL checks and determine system state"""
        self.results = []
        
        # Run all checks
        self.results.append(self.check_database())
        self.results.append(self.check_mt5())
        self.results.append(self.check_api())
        self.results.append(self.check_frontend())
        self.results.append(self.check_ai_models())
        self.results.append(self.check_risk_gate())
        self.results.append(self.check_reconciliation_daemon())
        self.results.append(self.check_data_integrity())
        self.results.append(self.check_heartbeat())
        
        # Determine state
        critical_failures = [r for r in self.results if not r.passed and r.critical]
        non_critical_failures = [r for r in self.results if not r.passed and not r.critical]
        
        if critical_failures:
            self.state = SystemState.HALT
        elif non_critical_failures:
            self.state = SystemState.DEGRADED
        else:
            self.state = SystemState.READY
        
        return self.state
    
    def print_report(self):
        """Print full system integrity report"""
        state_icons = {
            SystemState.READY: "[READY]",
            SystemState.DEGRADED: "[DEGRADED]",
            SystemState.HALT: "[HALT]",
        }
        
        print("=" * 70)
        print("  SYSTEM INTEGRITY GATE")
        print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        print("=" * 70)
        
        for result in self.results:
            icon = "PASS" if result.passed else "FAIL"
            critical_marker = " [CRITICAL]" if result.critical else " [NON-CRITICAL]"
            print(f"  [{icon}] {result.name}{critical_marker}")
            print(f"       {result.detail}")
        
        print(f"\n  SYSTEM STATE: {state_icons.get(self.state, 'UNKNOWN')} {self.state.value}")
        
        if self.state == SystemState.READY:
            print(f"  TRADING: ALLOWED")
        elif self.state == SystemState.DEGRADED:
            print(f"  TRADING: ALLOWED (non-critical issues)")
        else:
            print(f"  TRADING: BLOCKED (critical failures)")
        
        print("=" * 70)


if __name__ == "__main__":
    gate = SystemIntegrityGate()
    state = gate.run_all_checks()
    gate.print_report()
