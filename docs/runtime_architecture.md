# FOREX-AI-APP Runtime Architecture

> Last Updated: 2026-08-07 | Account: Live_Micro (Exness-MT5Real10)

## Service Map


## Port Assignments

| Service | Port | Technology | Purpose |
|---------|------|------------|---------|
| Frontend Dashboard | **3000** | React (CRA) | Trading UI & Monitoring |
| Node API Server | **8080** | Express.js | Backend API Gateway |
| AI Service | **8001** | FastAPI/Python | AI Engine & Signal Gen |

## Database

| Resource | Path | Engine |
|----------|------|--------|
| Trades DB | `ai-service/trades.db` | SQLite3 |

## Accounts

| Account | Server | Type | Balance |
|---------|--------|------|---------|
| REDACTED_LIVE_ACCOUNT | Exness-MT5Real10 | Live Micro | $19.19 |

## Service Dependencies


## Heartbeat Files

| Service | Heartbeat File |
|---------|---------------|
| Trading Daemon | `ai-service/trading_daemon_heartbeat.json` |
| Watchdog | `ai-service/watchdog_heartbeat.json` |
| Alerter | `ai-service/alerter_heartbeat.json` |

## Quick Commands

```bash
# Full diagnostics
.\ai-service\venv\Scripts\python.exe tools\diagnostics.py

# Start all services
start_all.bat

# Start Watchdog
.\ai-service\venv\Scripts\python.exe tools\watchdog.py

# Start Alerter
.\ai-service\venv\Scripts\python.exe tools\alerter.py

## Step 2: Create the Live Engine Monitor

```powershell
Set-Content -Path tools/live_monitor.py -Value @'
"""LIVE ENGINE MONITOR - Real-time trading system dashboard"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import get_db, check_mt5, check_service
from tools.heartbeat import Heartbeat, quick_heartbeat
from datetime import datetime, timezone
import time
import json
import os

class LiveMonitor:
    def __init__(self):
        self.heartbeat = Heartbeat("live_monitor")
        self.last_scan_time = None
        self.signals_generated = 0
        self.signals_passed = 0
        self.rejections = {
            "session": 0,
            "confidence": 0,
            "spread": 0,
            "news": 0,
            "regime": 0
        }
        self.orders_today = 0
        self.max_orders = 2  # Current daily limit
        
    def get_daemon_heartbeat_age(self):
        """Get seconds since last daemon heartbeat"""
        hb_file = Path("ai-service/trading_daemon_heartbeat.json")
        if not hb_file.exists():
            return None
        
        try:
            with open(hb_file, 'r') as f:
                data = json.load(f)
                last_hb = datetime.fromisoformat(data['last_heartbeat'])
                now = datetime.now(timezone.utc)
                return int((now - last_hb).total_seconds())
        except:
            return None
    
    def get_todays_stats(self):
        """Get today's trading statistics"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Today's trades
            cursor.execute("""
                SELECT COUNT(*), SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),
                       SUM(pnl), COUNT(DISTINCT pair)
                FROM trades 
                WHERE date(timestamp) = date('now')
            """)
            row = cursor.fetchone()
            today = {
                "total": row[0] or 0,
                "wins": row[1] or 0,
                "pnl": row[2] or 0,
                "pairs": row[3] or 0
            }
            
            # V3 trades specifically
            cursor.execute("""
                SELECT COUNT(*) FROM trades 
                WHERE strategy_version = 'V3_REGIME'
            """)
            v3_count = cursor.fetchone()[0]
            
            # PRE_V3 trades
            cursor.execute("""
                SELECT COUNT(*), SUM(pnl) FROM trades 
                WHERE strategy_version = 'PRE_V3'
            """)
            pre_v3 = cursor.fetchone()
            
            conn.close()
            
            return {
                "today": today,
                "v3_total": v3_count,
                "pre_v3_total": pre_v3[0] or 0,
                "pre_v3_pnl": pre_v3[1] or 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    def render(self):
        """Render the live monitor display"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 70)
        print("  FOREX-AI-APP LIVE ENGINE MONITOR")
        print("=" * 70)
        print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        # Row 1: Service Status
        print("+- SERVICES ---------------------------------------------+")
        
        # Daemon
        daemon = check_service("trading_daemon")
        daemon_icon = "??" if daemon["status"] == "ONLINE" else "??"
        hb_age = self.get_daemon_heartbeat_age()
        hb_str = f"{hb_age}s ago" if hb_age else "N/A"
        print(f"¦ Trading Daemon:    {daemon_icon} ONLINE  ¦ Heartbeat: {hb_str:<10} ¦")
        
        # MT5
        mt5 = check_mt5()
        mt5_icon = "??" if mt5["connected"] else "??"
        print(f"¦ MT5 Connection:    {mt5_icon} {mt5['server']:<20} ¦ Account: {mt5['account']} ¦")
        
        # Backend
        backend = check_service("backend_api")
        be_icon = "??" if backend["status"] == "ONLINE" else "??"
        print(f"¦ Backend API:       {be_icon} Port {backend['expected_port']:<5} ¦ PID: {backend['process']['pid'] if backend['process'] else 'N/A':<6} ¦")
        
        # Frontend
        frontend = check_service("frontend")
        fe_icon = "??" if frontend["status"] == "ONLINE" else "??"
        print(f"¦ Frontend:          {fe_icon} Port {frontend['expected_port']:<5} ¦ PID: {frontend['process']['pid'] if frontend['process'] else 'N/A':<6} ¦")
        
        print("+--------------------------------------------------------+")
        print()
        
        # Row 2: Signal Pipeline
        print("+- SIGNAL PIPELINE -------------------------------------+")
        print(f"¦ Last Scan:          {self.last_scan_time or 'No scans yet':<20}          ¦")
        print(f"¦ Signals Generated:  {self.signals_generated:<4}                               ¦")
        print(f"¦ Passed Filters:     {self.signals_passed:<4}                               ¦")
        print(f"¦                                                         ¦")
        print(f"¦ Rejected:                                                ¦")
        print(f"¦   Session Filter:   {self.rejections['session']:<4}                               ¦")
        print(f"¦   Confidence:       {self.rejections['confidence']:<4}                               ¦")
        print(f"¦   Spread:           {self.rejections['spread']:<4}                               ¦")
        print(f"¦   News:             {self.rejections['news']:<4}                               ¦")
        print(f"¦   Regime:           {self.rejections['regime']:<4}                               ¦")
        print("+--------------------------------------------------------+")
        print()
        
        # Row 3: Trading Activity
        stats = self.get_todays_stats()
        print("+- TRADING ACTIVITY ------------------------------------+")
        if "error" not in stats:
            t = stats["today"]
            win_rate = (t["wins"] / t["total"] * 100) if t["total"] > 0 else 0
            print(f"¦ Today's Orders:     {t['total']}/{self.max_orders:<4}  (limit: {self.max_orders})            ¦")
            print(f"¦ Win Rate Today:     {win_rate:.0f}% ({t['wins']}/{t['total']})                        ¦")
            print(f"¦ P&L Today:          ${t['pnl']:.2f}                               ¦")
            print(f"¦ Pairs Today:        {t['pairs']}                                       ¦")
            print(f"¦                                                         ¦")
            print(f"¦ V3_REGIME Trades:   {stats['v3_total']:<4}  (current strategy)              ¦")
            print(f"¦ PRE_V3 Trades:      {stats['pre_v3_total']:<4}  (PF 0.63, -$2227.27)         ¦")
        else:
            print(f"¦ Database Error: {stats['error']}                    ¦")
        print("+--------------------------------------------------------+")
        print()
        
        # Row 4: Validation Progress
        total_v3 = stats.get("v3_total", 0)
        milestones = [
            (10, "Execution Verified"),
            (25, "Risk Verified"),
            (50, "Initial Review"),
            (100, "Statistical Validation"),
            (300, "Production Confidence")
        ]
        
        print("+- V3 VALIDATION ROADMAP -------------------------------+")
        for target, label in milestones:
            if total_v3 >= target:
                icon = "?"
                bar = "¦" * 10
            else:
                icon = "?"
                progress = min(total_v3 / target, 1.0)
                filled = int(progress * 10)
                bar = "¦" * filled + "¦" * (10 - filled)
            
            print(f"¦ {icon} {label:<20} [{bar}] {total_v3}/{target}                     ¦")
        print("+--------------------------------------------------------+")
        
        print()
        print("  Press Ctrl+C to exit | Refreshing every 10 seconds")
        print("=" * 70)
    
    def run(self, interval=10):
        """Run the live monitor"""
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
