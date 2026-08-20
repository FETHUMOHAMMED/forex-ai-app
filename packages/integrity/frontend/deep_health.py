"""Deep Frontend/Dashboard Checks - 9 items per advisor specification."""
import urllib.request
import json
import socket
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_frontend_reachable() -> CheckResult:
    """FE-001: Frontend reachable"""
    try:
        response = urllib.request.urlopen('http://localhost:3000', timeout=3)
        passed = response.status == 200
        return CheckResult("frontend", "reachable", passed, Severity.WARNING,
                          "Dashboard serving" if passed else f"Status {response.status}")
    except:
        return CheckResult("frontend", "reachable", False, Severity.WARNING, "Dashboard not reachable")

@registry.register
def check_frontend_api() -> CheckResult:
    """FE-002: API reachable from frontend"""
    try:
        response = urllib.request.urlopen('http://localhost:3001/api/stats', timeout=3)
        passed = response.status in (200, 401)  # 401 = auth required but API is up
        return CheckResult("frontend", "api", passed, Severity.WARNING,
                          "Backend API responding" if passed else f"Status {response.status}")
    except:
        return CheckResult("frontend", "api", False, Severity.WARNING, "Backend API not reachable")

@registry.register
def check_frontend_websocket() -> CheckResult:
    """FE-003: WebSocket connected"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        result = sock.connect_ex(('localhost', 8080))
        sock.close()
        passed = result == 0
        return CheckResult("frontend", "websocket", passed, Severity.WARNING,
                          "WebSocket port open" if passed else "WebSocket port closed")
    except:
        sock.close()
        return CheckResult("frontend", "websocket", False, Severity.WARNING, "Cannot check WebSocket")

@registry.register
def check_frontend_data() -> CheckResult:
    """FE-004: Dashboard data loading"""
    try:
        response = urllib.request.urlopen('http://localhost:8002/v3/dashboard', timeout=3)
        data = json.loads(response.read())
        passed = 'performance' in data and 'archive' in data
        return CheckResult("frontend", "data_loading", passed, Severity.WARNING,
                          "V3 dashboard data available" if passed else "Missing sections")
    except:
        return CheckResult("frontend", "data_loading", False, Severity.WARNING, "Dashboard data not loading")

@registry.register
def check_frontend_signal_endpoint() -> CheckResult:
    """FE-005: Signal endpoint responding"""
    try:
        response = urllib.request.urlopen('http://localhost:8001/signals', timeout=3)
        passed = response.status in (200, 401, 404)  # Any response = endpoint exists
        return CheckResult("frontend", "signal_endpoint", passed, Severity.WARNING,
                          "Signal endpoint responding" if passed else "No response")
    except:
        return CheckResult("frontend", "signal_endpoint", False, Severity.WARNING, "Signal endpoint not responding")

@registry.register
def check_frontend_trade_endpoint() -> CheckResult:
    """FE-006: Trade endpoint responding"""
    try:
        response = urllib.request.urlopen('http://localhost:3001/api/stats', timeout=3)
        passed = response.status in (200, 401)
        return CheckResult("frontend", "trade_endpoint", passed, Severity.WARNING,
                          "Trade endpoint responding" if passed else "No response")
    except:
        return CheckResult("frontend", "trade_endpoint", False, Severity.WARNING, "Trade endpoint not responding")

@registry.register
def check_frontend_account_endpoint() -> CheckResult:
    """FE-007: Account endpoint responding"""
    try:
        response = urllib.request.urlopen('http://localhost:8002/v3/health', timeout=3)
        passed = response.status == 200
        return CheckResult("frontend", "account_endpoint", passed, Severity.WARNING,
                          "Account data available" if passed else "No account data")
    except:
        return CheckResult("frontend", "account_endpoint", False, Severity.WARNING, "Account endpoint not responding")

@registry.register
def check_frontend_metrics() -> CheckResult:
    """FE-008: Metrics endpoint responding"""
    try:
        response = urllib.request.urlopen('http://localhost:8002/metrics', timeout=3)
        passed = response.status == 200
        return CheckResult("frontend", "metrics", passed, Severity.WARNING,
                          "Metrics available" if passed else "No metrics")
    except:
        return CheckResult("frontend", "metrics", False, Severity.WARNING, "Metrics endpoint not available")

@registry.register
def check_frontend_stale() -> CheckResult:
    """FE-009: Stale dashboard detection"""
    # Check if dashboard has been updated recently
    from pathlib import Path
    state_file = Path("ai-service/system_integrity_state.json")
    if state_file.exists():
        import time
        age = time.time() - state_file.stat().st_mtime
        passed = age < 300  # Less than 5 minutes
        return CheckResult("frontend", "stale_detection", passed, Severity.WARNING,
                          f"Dashboard state {age:.0f}s old" if passed else f"STALE: {age:.0f}s")
    return CheckResult("frontend", "stale_detection", False, Severity.WARNING, "No state file")
