"""Continuous Reconciliation Daemon - Constantly verifies DB matches MT5.
Any divergence = CRITICAL alert + trading disabled for that account.
"""
import sqlite3
import MetaTrader5 as mt5
import time
from datetime import datetime, timezone
from enum import Enum

class DivergenceType(str, Enum):
    DB_POSITION_NOT_IN_MT5 = "DB_POSITION_NOT_IN_MT5"
    MT5_POSITION_NOT_IN_DB = "MT5_POSITION_NOT_IN_DB"
    PNL_MISMATCH = "PNL_MISMATCH"
    VOLUME_MISMATCH = "VOLUME_MISMATCH"
    ACCOUNT_MISMATCH = "ACCOUNT_MISMATCH"
    ENTRY_PRICE_MISMATCH = "ENTRY_PRICE_MISMATCH"

class ReconciliationDaemon:
    """Continuously reconciles DB with MT5. Divergence = HALT TRADING."""
    
    def __init__(self, db_path="ai-service/trades.db", check_interval=30):
        self.db_path = db_path
        self.check_interval = check_interval
        self.divergences = []
        self.trading_halted = False
        self.halted_accounts = set()
    
    def check_db_vs_mt5(self):
        """Compare database open positions with MT5 actual positions"""
        mt5.initialize()
        
        # Get MT5 positions
        mt5_positions = mt5.positions_get()
        mt5_tickets = {p.ticket for p in mt5_positions} if mt5_positions else set()
        
        # Get DB open positions
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT ticket, mt5_position_id, account, account_name, 
                   entry, volume, pnl, stop_loss, take_profit
            FROM trades 
            WHERE (result IS NULL OR result='' OR result='OPEN')
            AND strategy_version='V3_REGIME'
        """)
        db_open = c.fetchall()
        conn.close()
        
        for db_row in db_open:
            db_ticket = db_row[0]
            mt5_pos_id = db_row[1]
            account = db_row[2]
            entry = db_row[4]
            volume = db_row[5]
            
            # Check: DB says OPEN, is position in MT5?
            if mt5_pos_id not in mt5_tickets:
                self._raise_divergence(
                    DivergenceType.DB_POSITION_NOT_IN_MT5,
                    account, f"DB position {mt5_pos_id} is OPEN in DB but NOT in MT5"
                )
                continue
            
            # Position exists in MT5 - verify details
            mt5_pos = [p for p in mt5_positions if p.ticket == mt5_pos_id][0]
            
            # Volume check
            if abs(mt5_pos.volume - volume) > 0.001:
                self._raise_divergence(
                    DivergenceType.VOLUME_MISMATCH,
                    account, f"Volume: DB={volume} MT5={mt5_pos.volume}"
                )
            
            # Entry price check
            if entry and abs(mt5_pos.price_open - entry) > 0.0001:
                self._raise_divergence(
                    DivergenceType.ENTRY_PRICE_MISMATCH,
                    account, f"Entry: DB={entry} MT5={mt5_pos.price_open}"
                )
        
        # Check: MT5 positions NOT in DB (orphans)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT mt5_position_id FROM trades WHERE mt5_position_id IS NOT NULL")
        db_tickets = {r[0] for r in c.fetchall()}
        conn.close()
        
        for mt5_ticket in mt5_tickets:
            if mt5_ticket not in db_tickets:
                self._raise_divergence(
                    DivergenceType.MT5_POSITION_NOT_IN_DB,
                    "Unknown", f"MT5 position {mt5_ticket} not in database (ORPHAN)"
                )
        
        mt5.shutdown()
        return self.divergences
    
    def _raise_divergence(self, div_type, account, detail):
        """Raise divergence and halt trading for affected account"""
        div = {
            "type": div_type.value,
            "account": account,
            "detail": detail,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }
        self.divergences.append(div)
        self.halted_accounts.add(account)
        self.trading_halted = True
        print(f"[CRITICAL] {div_type.value}: {detail}")
        print(f"[CRITICAL] Trading HALTED for account: {account}")
    
    def run_continuously(self):
        """Run reconciliation checks forever"""
        print(f"[RECON DAEMON] Starting continuous reconciliation (every {self.check_interval}s)")
        print(f"[RECON DAEMON] Any divergence = HALT TRADING")
        print()
        
        while True:
            self.divergences = []
            self.check_db_vs_mt5()
            
            if self.trading_halted:
                print(f"\n[HALTED] Trading disabled for: {self.halted_accounts}")
                print(f"[HALTED] {len(self.divergences)} divergence(s) detected")
                for d in self.divergences:
                    print(f"  - {d['type']}: {d['detail']}")
                print(f"[HALTED] Manual intervention required to resume")
            else:
                print(f"[OK] DB matches MT5. No divergence. Trading allowed.")
            
            time.sleep(self.check_interval)
    
    def get_status(self):
        return {
            "trading_halted": self.trading_halted,
            "halted_accounts": list(self.halted_accounts),
            "divergence_count": len(self.divergences),
            "divergences": self.divergences,
        }


# ============================================================================
# TEST
# ============================================================================
if __name__ == "__main__":
    daemon = ReconciliationDaemon(check_interval=5)
    daemon.check_db_vs_mt5()
    
    status = daemon.get_status()
    print("\n" + "=" * 65)
    print("  RECONCILIATION DAEMON STATUS")
    print("=" * 65)
    print(f"  Trading halted: {status['trading_halted']}")
    print(f"  Halted accounts: {status['halted_accounts']}")
    print(f"  Divergences: {status['divergence_count']}")
    if status['divergences']:
        for d in status['divergences']:
            print(f"    [{d['type']}] {d['detail']}")
    print("=" * 65)
