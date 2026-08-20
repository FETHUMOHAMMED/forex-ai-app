"""MT5 connection check"""
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_mt5_connection() -> CheckResult:
    import MetaTrader5 as mt5
    try:
        if not mt5.initialize():
            return CheckResult("mt5", "connection", False, Severity.CRITICAL, "MT5 not initialized")
        info = mt5.account_info()
        mt5.shutdown()
        if not info:
            return CheckResult("mt5", "connection", False, Severity.CRITICAL, "No account info")
        return CheckResult("mt5", "connection", True, Severity.CRITICAL,
                          f"Account {info.login} balance=${info.balance}")
    except Exception as e:
        return CheckResult("mt5", "connection", False, Severity.CRITICAL, str(e))
