# -*- coding: utf-8 -*-
"""LIVE ENGINE MONITOR - Production-grade trading dashboard"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import get_db, check_mt5, check_service
from tools.heartbeat import Heartbeat, get_heartbeat_status, classify_heartbeat
from tools.validation_mode import get_validation_status
from datetime import datetime, timezone
import time
import json
import os

class LiveMonitor:
    def __init__(self):
        self.heartbeat = Heartbeat("live_monitor")
        
    def render(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        
        now = datetime.now(timezone.utc)
        
        print("=" * 75)
        print("  FOREX-AI-APP LIVE ENGINE MONITOR")
        print("=" * 75)
        print(f"  {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        # === SERVICES ===
        print("=== SERVICES ===")
        
        # Trading Daemon with heartbeat classification
        hb_status = get_heartbeat_status("trading_daemon")
        daemon = check_service("trading_daemon")
        d_icon = "[ONLINE]" if daemon["status"] == "ONLINE" else "[OFFLINE]"
        
        if hb_status['age_seconds'] is not None:
            hb_icon = hb_status['icon']
            hb_str = f"{hb_status['age_seconds']}s [{hb_status['status']}]"
        else:
            hb_icon = "[NO HB]"
            hb_str = "NO HEARTBEAT"
        
        print(f"  Trading Daemon  {d_icon}  {hb_icon} Heartbeat: {hb_str}")
        
        if hb_status['status'] in ['WARNING', 'STALE', 'OFFLINE']:
            print(f"    [!] Daemon may need attention!")
        
        # MT5
        mt5 = check_mt5()
        m_icon = "[ONLINE]" if mt5["connected"] else "[OFFLINE]"
        print(f"  MT5 Connection  {m_icon}  {mt5['account']} @ {mt5['server']}")
        if mt5['connected']:
            print(f"                  Balance: ${mt5['balance']:,.2f}  Equity: ${mt5['equity']:,.2f}")
        
        # Backend
        backend = check_service("backend_api")
        b_icon = "[ONLINE]" if backend["status"] == "ONLINE" else "[OFFLINE]"
        print(f"  Backend API     {b_icon}  Port {backend['expected_port']}")
        
        # Frontend
        frontend = check_service("frontend")
        f_icon = "[ONLINE]" if frontend["status"] == "ONLINE" else "[OFFLINE]"
        print(f"  Frontend        {f_icon}  Port {frontend['expected_port']}")
        
        print()
        
        # === VALIDATION STATUS ===
        validation = get_validation_status()
        print("=== V3 VALIDATION PROGRESS ===")
        print(f"  Mode: {validation['mode']} | Daily Limit: {validation['daily_limit']} trades")
        print(f"  V3 Trades: {validation['total_trades']} | Win Rate: {validation['win_rate']}% | PF: {validation['profit_factor']}")
        
        if validation['next_milestone']:
            next_ms = validation['next_milestone']
            needed = validation['trades_needed']
            pct = (validation['total_trades'] / next_ms[0]) * 100
            bar_len = 40
            filled = int((validation['total_trades'] / next_ms[0]) * bar_len)
            bar = "#" * filled + "-" * (bar_len - filled)
            print(f"  Next: {next_ms[1]}")
            print(f"  [{bar}] {validation['total_trades']}/{next_ms[0]} ({pct:.0f}%) - ~{needed} trades to go")
        
        print()
        
        # === TODAY'S ACTIVITY ===
        print("=== TODAY'S ACTIVITY ===")
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*), SUM(pnl), 
                       SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END)
                FROM trades 
                WHERE date(timestamp) = date('now')
                AND strategy_version = 'V3_REGIME'
                AND environment LIKE 'LIVE_MICRO%'
            """)
            today = cursor.fetchone()
            
            daily_total = today[0] or 0
            daily_pnl = today[1] or 0
            daily_wins = today[2] or 0
            daily_wr = (daily_wins / daily_total * 100) if daily_total > 0 else 0
            
            bar_len = 20
            filled = int((daily_total / validation['daily_limit']) * bar_len)
            bar = "=" * filled + "-" * (bar_len - filled)
            
            print(f"  Orders:          [{bar}] {daily_total}/{validation['daily_limit']}")
            print(f"  Win Rate:        {daily_wr:.0f}%")
            print(f"  P&L:             ${daily_pnl:,.2f}")
            
            # Recent V3 trades
            cursor.execute("""
                SELECT pair, signal, result, pnl, timestamp 
                FROM trades 
                WHERE strategy_version = 'V3_REGIME'
                AND environment LIKE 'LIVE_MICRO%'
                ORDER BY timestamp DESC LIMIT 5
            """)
            recent = cursor.fetchall()
            
            if recent:
                print(f"\n  Recent V3 Trades:")
                for trade in recent:
                    pair, signal, result, pnl, ts = trade
                    icon = "[WIN]" if result == "WIN" else "[LOSS]" if result == "LOSS" else "[OPEN]"
                    pnl_str = f"${pnl:+,.2f}" if pnl else "$0.00"
                    print(f"    {icon} {pair:<8} {signal:<5} {pnl_str:<10}")
            
            conn.close()
        except Exception as e:
            print(f"  DB Error: {e}")
        
        print()
        print("  Ctrl+C to exit | Refreshing every 10s")
        print("=" * 75)
    
    def run(self, interval=10):
        self.heartbeat.start(interval_seconds=30)
        try:
            while True:
                self.render()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\nMonitor stopped.")
        finally:
            self.heartbeat.stop()

if __name__ == "__main__":
    monitor = LiveMonitor()
    monitor.run()
