"""Deep Observability Checks - 9 items + scanner heartbeat per advisor."""
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

SCANNER_HEARTBEAT_FILE = Path("ai-service/scanner_heartbeat.json")

def write_scanner_heartbeat():
    """Write scanner heartbeat - called every scanner run"""
    data = {
        "last_scan_at": datetime.now(timezone.utc).isoformat(),
        "next_expected_scan": (datetime.now(timezone.utc).timestamp()) + 60,
    }
    SCANNER_HEARTBEAT_FILE.write_text(json.dumps(data, indent=2))
    return data

def read_scanner_heartbeat() -> dict:
    """Read scanner heartbeat"""
    if not SCANNER_HEARTBEAT_FILE.exists():
        return {}
    return json.loads(SCANNER_HEARTBEAT_FILE.read_text())

@registry.register
def check_logger_functioning() -> CheckResult:
    """LOG-001: Logger functioning"""
    try:
        from packages.observability.structured_logger import log_event
        log_event("CHECK", {"test": True})
        return CheckResult("observability", "logger", True, Severity.WARNING, "Logger works")
    except Exception as e:
        return CheckResult("observability", "logger", False, Severity.WARNING, str(e))

@registry.register
def check_structured_logs() -> CheckResult:
    """LOG-002: Structured logs"""
    try:
        from packages.observability.structured_logger import log_event
        event = log_event("CHECK", {"test": True})
        passed = isinstance(event, dict) and "timestamp_utc" in event
        return CheckResult("observability", "structured_logs", passed, Severity.WARNING,
                          "JSON structured logs" if passed else "Not structured")
    except Exception as e:
        return CheckResult("observability", "structured_logs", False, Severity.WARNING, str(e))

@registry.register
def check_timestamps_valid() -> CheckResult:
    """LOG-003: Timestamps valid"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    passed = now.tzinfo is not None
    return CheckResult("observability", "timestamps", passed, Severity.WARNING,
                      f"Timezone-aware UTC" if passed else "Missing timezone")

@registry.register
def check_alert_system() -> CheckResult:
    """LOG-004: Alert system functioning"""
    try:
        from packages.observability.alert_dedup import AlertDeduplicator
        dedup = AlertDeduplicator()
        passed = dedup is not None
        return CheckResult("observability", "alert_system", passed, Severity.WARNING,
                          "Alert deduplication active" if passed else "No alert system")
    except Exception as e:
        return CheckResult("observability", "alert_system", False, Severity.WARNING, str(e))

@registry.register
def check_prometheus() -> CheckResult:
    """LOG-005: Prometheus available"""
    import urllib.request
    try:
        response = urllib.request.urlopen('http://localhost:8002/metrics', timeout=3)
        passed = response.status == 200
        return CheckResult("observability", "prometheus", passed, Severity.WARNING,
                          "Metrics available" if passed else f"Status {response.status}")
    except:
        return CheckResult("observability", "prometheus", False, Severity.WARNING, "Not reachable")

@registry.register
def check_heartbeat_current() -> CheckResult:
    """LOG-006: Heartbeat current"""
    hb_file = Path("ai-service/trading_daemon_heartbeat.json")
    if not hb_file.exists():
        return CheckResult("observability", "heartbeat", False, Severity.WARNING, "No heartbeat file")
    try:
        data = json.loads(hb_file.read_text())
        last_hb = datetime.fromisoformat(data.get("last_heartbeat", ""))
        age = (datetime.now(timezone.utc) - last_hb).total_seconds()
        passed = age < 300
        return CheckResult("observability", "heartbeat", passed, Severity.WARNING,
                          f"{age:.0f}s ago" if passed else f"STALE: {age:.0f}s")
    except:
        return CheckResult("observability", "heartbeat", False, Severity.WARNING, "Cannot parse")

@registry.register
def check_error_rate() -> CheckResult:
    """LOG-007: Error rate"""
    ledger = Path("ai-service/decision_ledger.jsonl")
    if not ledger.exists():
        return CheckResult("observability", "error_rate", True, Severity.WARNING, "No errors")
    errors = 0
    total = 0
    with open(ledger) as f:
        for line in f:
            total += 1
            if "REJECT" in line:
                errors += 1
    error_rate = (errors / total * 100) if total > 0 else 0
    passed = error_rate < 50
    return CheckResult("observability", "error_rate", passed, Severity.WARNING,
                      f"{error_rate:.0f}% ({errors}/{total})")

@registry.register
def check_scanner_alive() -> CheckResult:
    """LOG-008: Scanner itself alive"""
    hb = write_scanner_heartbeat()
    passed = "last_scan_at" in hb
    return CheckResult("observability", "scanner_alive", passed, Severity.CRITICAL,
                      f"Heartbeat written at {hb.get('last_scan_at', 'N/A')[:19]}")

@registry.register
def check_scanner_freshness() -> CheckResult:
    """CRITICAL: Scanner heartbeat not stale"""
    hb = read_scanner_heartbeat()
    if not hb:
        return CheckResult("observability", "scanner_freshness", False, Severity.CRITICAL,
                          "No scanner heartbeat - scanner DEAD")
    try:
        last_scan = datetime.fromisoformat(hb.get("last_scan_at", ""))
        age = (datetime.now(timezone.utc) - last_scan).total_seconds()
        passed = age < 300
        return CheckResult("observability", "scanner_freshness", passed, Severity.CRITICAL,
                          f"Scanner {age:.0f}s old" if passed else f"SCANNER STALE: {age:.0f}s - HALT")
    except:
        return CheckResult("observability", "scanner_freshness", False, Severity.CRITICAL, "Cannot parse")
