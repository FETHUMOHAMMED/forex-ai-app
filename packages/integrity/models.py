"""Check result model"""
from dataclasses import dataclass
from datetime import datetime, timezone
from .severity import Severity

@dataclass
class CheckResult:
    domain: str
    check: str
    passed: bool
    severity: Severity
    detail: str = ""
    checked_at: str = ""
    
    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now(timezone.utc).isoformat()
