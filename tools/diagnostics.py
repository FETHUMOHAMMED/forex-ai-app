"""FOREX-AI-APP Unified Diagnostics - One command health check"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import get_db, check_mt5, check_daemon, check_backend
from datetime import datetime

def main():
    print("=" * 60)
    print("  FOREX-AI-APP UNIFIED DIAGNOSTICS")
    print("=" * 60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Database Check
    print("\n[1/4] Database Connection...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT pair) FROM trades")
        pair_count = cursor.fetchone()[0]
        print(f"  ? Connected - {trade_count} trades across {pair_count} pairs")
        conn.close()
    except Exception as e:
        print(f"  ? Failed: {e}")
    
    # 2. MT5 Check
    print("\n[2/4] MT5 Connection...")
    mt5_status = check_mt5()
    if mt5_status['connected']:
        print(f"  ? Connected - Account {mt5_status['account']}")
        print(f"    Balance: ${mt5_status['balance']:.2f}")
        print(f"    Equity: ${mt5_status['equity']:.2f}")
        print(f"    Server: {mt5_status['server']}")
    else:
        print(f"  ? Not connected")
    
    # 3. Trading Daemon
    print("\n[3/4] Trading Daemon...")
    daemon = check_daemon()
    if daemon['running']:
        print(f"  ? Running (PID: {daemon['pid']})")
    else:
        print(f"  ? Not running")
    
    # 4. Backend Service
    print("\n[4/4] Backend Service...")
    backend = check_backend()
    if backend['running']:
        print(f"  ? Running at {backend['url']}")
    else:
        print(f"  ? Not running")
    
    print("\n" + "=" * 60)
    print("  Diagnostics Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
