"""Test the watchdog by simulating service status"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import SERVICES, check_service
from tools.alerter import ServiceAlerter

print("=" * 60)
print("  WATCHDOG & ALERTER TEST")
print("=" * 60)

# Test service status detection
print("\nCurrent Service Status:")
for key in SERVICES:
    status = check_service(key)
    print(f"  {SERVICES[key]['name']}: {status['status']}")

# Test alerter
print("\nTesting Alerter...")
alerter = ServiceAlerter(alert_interval=0)  # No rate limiting for test
alerter.check_services()
print("  ? Alert check complete")

print("\n" + "=" * 60)
print("  Watchdog system ready!")
print("  Start with: .\\ai-service\\venv\\Scripts\\python.exe tools\\watchdog.py")
print("  Alerter: .\\ai-service\\venv\\Scripts\\python.exe tools\\alerter.py")
print("=" * 60)
