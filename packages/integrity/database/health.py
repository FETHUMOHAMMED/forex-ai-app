"""Database health check"""
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_database_health() -> CheckResult:
    import sqlite3
    try:
        conn = sqlite3.connect('ai-service/trades.db', timeout=5)
        c = conn.cursor()
        c.execute("PRAGMA integrity_check")
        integrity = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM trades")
        count = c.fetchone()[0]
        conn.close()
        passed = integrity == 'ok'
        return CheckResult("database", "health", passed, Severity.CRITICAL,
                          f"{count} trades, integrity={integrity}")
    except Exception as e:
        return CheckResult("database", "health", False, Severity.CRITICAL, str(e))
