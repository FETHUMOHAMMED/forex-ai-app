"""FOREX-AI-APP Unified Diagnostics - Heartbeat-aware health monitoring"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import (
    get_db, check_mt5, check_service, SERVICES,
    find_process_by_script
)
from datetime import datetime, timezone

def print_service_status(service_key):
    """Pretty print service status"""
    status = check_service(service_key)
    service = SERVICES[service_key]
    
    print(f"\n{service['name']}")
    print(f"  Status: {status['status']}")
    
    if service.get('expected_port'):
        print(f"  Expected Port: {service['expected_port']}")
    
    if status.get('process'):
        proc = status['process']
        print(f"  Process: {' '.join(proc['cmdline'][:3])}...")
        print(f"  PID: {proc['pid']}")
        print(f"  Started: {proc['start_time'].strftime('%Y-%m-%d %H:%M UTC')}")
    
    if status.get('last_heartbeat'):
        print(f"  Last Heartbeat: {status['last_heartbeat']}")


def main():
    print("=" * 60)
    print("  FOREX-AI-APP UNIFIED DIAGNOSTICS")
    print("=" * 60)
    print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    
    # 1. Database Check
    print("\n[1/6] Database Connection...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT pair) FROM trades")
        pair_count = cursor.fetchone()[0]
        
        # Latest trade
        cursor.execute("SELECT timestamp FROM trades ORDER BY timestamp DESC LIMIT 1")
        last_trade = cursor.fetchone()
        last_trade_time = last_trade[0] if last_trade else "N/A"
        
        print(f"  ? Connected")
        print(f"    Total Trades: {trade_count}")
        print(f"    Pairs Traded: {pair_count}")
        print(f"    Last Trade: {last_trade_time}")
        conn.close()
    except Exception as e:
        print(f"  ? Failed: {e}")
    
    # 2. MT5 Check
    print("\n[2/6] MT5 Connection...")
    mt5_status = check_mt5()
    if mt5_status['connected']:
        print(f"  ? Connected")
        print(f"    Account: {mt5_status['account']}")
        print(f"    Balance: ${mt5_status['balance']:,.2f}")
        print(f"    Equity: ${mt5_status['equity']:,.2f}")
        print(f"    Server: {mt5_status['server']}")
    else:
        print(f"  ? Not connected")
    
    # 3. Trading Daemon
    print("\n[3/6] Trading Daemon...")
    print_service_status("trading_daemon")
    
    # 4. Backend API
    print("\n[4/6] Backend API...")
    print_service_status("backend_api")
    
    # 5. Frontend Dashboard
    print("\n[5/6] Frontend Dashboard...")
    print_service_status("frontend")
    
    # 6. Backend Server
    print("\n[6/6] Backend Server (Node)...")
    print_service_status("backend_server")
    
    # Summary
    print("\n" + "=" * 60)
    services_online = sum(
        1 for s in SERVICES 
        if check_service(s)["status"] == "ONLINE"
    )
    print(f"  Services Online: {services_online}/{len(SERVICES)}")
    print(f"  MT5: {'?' if mt5_status['connected'] else '?'}")
    print(f"  Database: ?")
    print("=" * 60)

if __name__ == "__main__":
    main()
