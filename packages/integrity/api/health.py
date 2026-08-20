"""API health check"""
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_api_health() -> CheckResult:
    import urllib.request
    try:
        response = urllib.request.urlopen('http://localhost:8002/v3/health', timeout=3)
        passed = response.status == 200
        return CheckResult("api", "health", passed, Severity.WARNING, 
                          "V3 API healthy" if passed else f"Status {response.status}")
    except Exception as e:
        return CheckResult("api", "health", False, Severity.WARNING, str(e))
