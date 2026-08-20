"""Startup Verification - Run after system boot to verify everything"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import check_service, check_mt5, get_db
import time

print("=" * 60)
print("  STARTUP VERIFICATION")
print("=" * 60)

checks = [
    ("Trading Daemon", "trading_daemon"),
    ("Backend API", "backend_api"),
    ("Frontend", "frontend"),
    ("Backend Server", "backend_server"),
]

all_ok = True

for name, key in checks:
    print(f"\nChecking {name}...", end=" ")
    status = check_service(key)
    if status["status"] == "ONLINE":
        print("? ONLINE")
    else:
        print(f"? {status['status']}")
        all_ok = False

print(f"\nChecking MT5...", end=" ")
mt5 = check_mt5()
if mt5["connected"]:
    print(f"? Connected (Account {mt5['account']})")
else:
    print("? Not connected")
    all_ok = False

print(f"\nChecking Database...", end=" ")
try:
    conn = get_db()
    conn.close()
    print("? Accessible")
except Exception as e:
    print(f"? {e}")
    all_ok = False

print("\n" + "=" * 60)
if all_ok:
    print("  ALL SYSTEMS GO ?")
    print("  Ready for trading!")
else:
    print("  ? SOME SYSTEMS OFFLINE - Check logs")
print("=" * 60)
