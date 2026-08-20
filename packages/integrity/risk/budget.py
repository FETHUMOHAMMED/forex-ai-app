"""Risk gate check"""
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_risk_gate() -> CheckResult:
    try:
        import sys
        sys.path.insert(0, '.')
        from packages.risk.validation_lock import VALIDATION_LIMITS
        return CheckResult("risk", "budget", True, Severity.CRITICAL,
                          f"Max vol={VALIDATION_LIMITS.max_volume}")
    except Exception as e:
        return CheckResult("risk", "budget", False, Severity.CRITICAL, str(e))
