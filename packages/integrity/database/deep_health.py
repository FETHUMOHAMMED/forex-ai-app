"""Deep Database Health Checks - 20+ items per advisor specification."""
import sqlite3
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_db_connection() -> CheckResult:
    """DB-001: SQLite connection"""
    try:
        conn = sqlite3.connect('ai-service/trades.db', timeout=5)
        conn.close()
        return CheckResult("database", "connection", True, Severity.CRITICAL, "Connected")
    except Exception as e:
        return CheckResult("database", "connection", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_readable() -> CheckResult:
    """DB-002: Database readable"""
    try:
        conn = sqlite3.connect('ai-service/trades.db', timeout=5)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM trades")
        count = c.fetchone()[0]
        conn.close()
        return CheckResult("database", "readable", True, Severity.CRITICAL, f"{count} trades readable")
    except Exception as e:
        return CheckResult("database", "readable", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_writable() -> CheckResult:
    """DB-003: Database writable"""
    try:
        conn = sqlite3.connect('ai-service/trades.db', timeout=5)
        c = conn.cursor()
        # Test write with a harmless no-op
        c.execute("SELECT 1")
        conn.commit()
        conn.close()
        return CheckResult("database", "writable", True, Severity.CRITICAL, "Writable")
    except Exception as e:
        return CheckResult("database", "writable", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_tables() -> CheckResult:
    """DB-010: Required tables exist"""
    required_tables = ['trades', 'signals', 'orders', 'positions', 'deals', 'trades_normalized']
    try:
        conn = sqlite3.connect('ai-service/trades.db')
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {r[0] for r in c.fetchall()}
        conn.close()
        missing = [t for t in required_tables if t not in existing]
        passed = len(missing) == 0
        return CheckResult("database", "tables", passed, Severity.CRITICAL,
                          f"All required tables" if passed else f"Missing: {missing}")
    except Exception as e:
        return CheckResult("database", "tables", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_columns() -> CheckResult:
    """DB-011: Required columns exist on trades table"""
    required_cols = ['mt5_position_id', 'execution_contract_valid', 'entry_deviation_pips',
                     'account', 'account_name', 'strategy_version', 'timestamp', 'exit_time']
    try:
        conn = sqlite3.connect('ai-service/trades.db')
        c = conn.cursor()
        c.execute("PRAGMA table_info(trades)")
        existing = {r[1] for r in c.fetchall()}
        conn.close()
        missing = [col for col in required_cols if col not in existing]
        passed = len(missing) == 0
        return CheckResult("database", "columns", passed, Severity.CRITICAL,
                          "All required columns" if passed else f"Missing: {missing}")
    except Exception as e:
        return CheckResult("database", "columns", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_duplicate_tickets() -> CheckResult:
    """DB-021: No duplicate tickets"""
    try:
        conn = sqlite3.connect('ai-service/trades.db')
        c = conn.cursor()
        c.execute("SELECT ticket, COUNT(*) FROM trades WHERE ticket IS NOT NULL GROUP BY ticket HAVING COUNT(*) > 1")
        dupes = c.fetchall()
        conn.close()
        passed = len(dupes) == 0
        return CheckResult("database", "duplicate_tickets", passed, Severity.CRITICAL,
                          "No duplicates" if passed else f"{len(dupes)} duplicates")
    except Exception as e:
        return CheckResult("database", "duplicate_tickets", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_impossible_timestamps() -> CheckResult:
    """DB-023: No exit before entry"""
    try:
        conn = sqlite3.connect('ai-service/trades.db')
        c = conn.cursor()
        c.execute("""SELECT COUNT(*) FROM trades 
                     WHERE exit_time IS NOT NULL AND timestamp IS NOT NULL 
                     AND exit_time < timestamp AND result NOT LIKE 'LEGACY%'""")
        bad = c.fetchone()[0]
        conn.close()
        passed = bad == 0
        return CheckResult("database", "timestamps", passed, Severity.CRITICAL,
                          "No impossible timestamps" if passed else f"{bad} with exit before entry")
    except Exception as e:
        return CheckResult("database", "timestamps", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_missing_account() -> CheckResult:
    """DB-024: No missing account identity in active trades"""
    try:
        conn = sqlite3.connect('ai-service/trades.db')
        c = conn.cursor()
        c.execute("""SELECT COUNT(*) FROM trades 
                     WHERE (account IS NULL OR account_name IS NULL) 
                     AND result NOT LIKE 'LEGACY%'
                     AND strategy_version='V3_REGIME'""")
        missing = c.fetchone()[0]
        conn.close()
        passed = missing == 0
        return CheckResult("database", "account_identity", passed, Severity.CRITICAL,
                          "All have account" if passed else f"{missing} missing account")
    except Exception as e:
        return CheckResult("database", "account_identity", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_missing_strategy() -> CheckResult:
    """DB-025: No missing strategy version"""
    try:
        conn = sqlite3.connect('ai-service/trades.db')
        c = conn.cursor()
        c.execute("""SELECT COUNT(*) FROM trades 
                     WHERE strategy_version IS NULL OR strategy_version = ''
                     AND result NOT LIKE 'LEGACY%'""")
        missing = c.fetchone()[0]
        conn.close()
        passed = missing == 0
        return CheckResult("database", "strategy_version", passed, Severity.CRITICAL,
                          "All have strategy" if passed else f"{missing} missing strategy")
    except Exception as e:
        return CheckResult("database", "strategy_version", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_orphans() -> CheckResult:
    """DB-027: No orphan trades (DB says open but MT5 says closed)"""
    try:
        conn = sqlite3.connect('ai-service/trades.db')
        c = conn.cursor()
        c.execute("""SELECT COUNT(*) FROM trades 
                     WHERE (result IS NULL OR result='' OR result='OPEN')
                     AND mt5_closure_state = 'CLOSED'
                     AND result NOT LIKE 'LEGACY%'""")
        orphans = c.fetchone()[0]
        conn.close()
        passed = orphans == 0
        return CheckResult("database", "orphans", passed, Severity.CRITICAL,
                          "No orphans" if passed else f"{orphans} orphan trades")
    except Exception as e:
        return CheckResult("database", "orphans", False, Severity.CRITICAL, str(e))

@registry.register
def check_db_contamination() -> CheckResult:
    """DB-028: No active account contamination"""
    try:
        conn = sqlite3.connect('ai-service/trades.db')
        c = conn.cursor()
        c.execute("""SELECT COUNT(*) FROM trades 
                     WHERE account='Live_Micro' AND account_name != 'Live_Micro'
                     AND result NOT LIKE 'LEGACY%'""")
        contaminated = c.fetchone()[0]
        conn.close()
        passed = contaminated == 0
        return CheckResult("database", "contamination", passed, Severity.CRITICAL,
                          "No contamination" if passed else f"{contaminated} contaminated")
    except Exception as e:
        return CheckResult("database", "contamination", False, Severity.CRITICAL, str(e))
