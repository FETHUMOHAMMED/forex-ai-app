"""Frontend dashboard check"""
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_frontend() -> CheckResult:
    import urllib.request
    try:
        response = urllib.request.urlopen('http://localhost:3000', timeout=3)
        passed = response.status == 200
        return CheckResult("frontend", "dashboard", passed, Severity.WARNING,
                          "Dashboard serving" if passed else f"Status {response.status}")
    except:
        return CheckResult("frontend", "dashboard", False, Severity.WARNING, "Not reachable")
