"""System decision from all check results"""
from enum import Enum
from .severity import Severity
from .models import CheckResult

class SystemDecision(str, Enum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    HALT = "HALT"

def make_decision(results: list) -> SystemDecision:
    """Determine system state from check results"""
    critical_fails = [r for r in results if not r.passed and r.severity == Severity.CRITICAL]
    warning_fails = [r for r in results if not r.passed and r.severity == Severity.WARNING]
    
    if critical_fails:
        return SystemDecision.HALT
    elif warning_fails:
        return SystemDecision.DEGRADED
    return SystemDecision.READY
