"""Bug Dashboard - Complete System Health Monitor"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import get_db, check_mt5, check_daemon, check_backend

def main():
    print("=" * 50)
    print("  BUG DASHBOARD - System Health Monitor")
    print("=" * 50)
    
    # Check MT5
    mt5_status = check_mt5()
    print(f"\nMT5 Connection: {'PASS' if mt5_status['connected'] else 'FAIL'}")
    if mt5_status['connected']:
        print(f"  Account: {mt5_status['account']}")
        print(f"  Balance: ${mt5_status['balance']:.2f}")
        print(f"  Equity: ${mt5_status['equity']:.2f}")
        print(f"  Server: {mt5_status['server']}")
    
    # Check Database
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        print(f"\nDatabase: PASS")
        print(f"  Total Trades: {trade_count}")
        conn.close()
    except Exception as e:
        print(f"\nDatabase: FAIL - {e}")
    
    # Check Daemon
    daemon_status = check_daemon()
    print(f"\nTrading Daemon: {'PASS' if daemon_status['running'] else 'NOT RUNNING'}")
    
    # Check Backend
    backend_status = check_backend()
    print(f"Backend Service: {'PASS' if backend_status['running'] else 'NOT RUNNING'}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
