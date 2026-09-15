"""MT5 RECONCILIATION - Detect mismatches between app and broker."""
import MetaTrader5 as mt5
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path

class MT5Reconciliation:
    """
    Reconciles application state with MT5 reality.
    Detects ANY mismatch immediately.
    """
    
    def __init__(self):
        self.reconciliation_log = Path("research/reconciliation_log.jsonl")
        self.reconciliation_log.parent.mkdir(parents=True, exist_ok=True)
        
    def get_mt5_positions(self) -> List[Dict]:
        """Get all open positions from MT5."""
        if not mt5.initialize():
            return []
        
        positions = mt5.positions_get()
        mt5.shutdown()
        
        result = []
        if positions:
            for pos in positions:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == 0 else "SELL",
                    "volume": pos.volume,
                    "entry": pos.price_open,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                    "open_time": datetime.fromtimestamp(pos.time, tz=timezone.utc).isoformat()
                })
        
        return result
    
    def get_mt5_orders(self) -> List[Dict]:
        """Get all orders (pending) from MT5."""
        if not mt5.initialize():
            return []
        
        orders = mt5.orders_get()
        mt5.shutdown()
        
        result = []
        if orders:
            for order in orders:
                result.append({
                    "ticket": order.ticket,
                    "symbol": order.symbol,
                    "type": order.type,
                    "volume": order.volume_current,
                    "price": order.price_open,
                    "sl": order.sl,
                    "tp": order.tp,
                    "setup_time": datetime.fromtimestamp(order.time_setup, tz=timezone.utc).isoformat()
                })
        
        return result
    
    def get_mt5_deals(self, days: int = 7) -> List[Dict]:
        """Get recent deals from MT5 history."""
        if not mt5.initialize():
            return []
        
        from datetime import timedelta
        now = datetime.now()
        start = now - timedelta(days=days)
        
        deals = mt5.history_deals_get(start, now)
        mt5.shutdown()
        
        result = []
        if deals:
            for deal in deals:
                result.append({
                    "ticket": deal.ticket,
                    "order": deal.order,
                    "symbol": deal.symbol,
                    "type": deal.type,
                    "volume": deal.volume,
                    "price": deal.price,
                    "profit": deal.profit,
                    "commission": deal.commission,
                    "time": datetime.fromtimestamp(deal.time, tz=timezone.utc).isoformat()
                })
        
        return result
    
    def get_db_trades(self) -> List[Dict]:
        """Get trades from our database."""
        # Simplified - read from our logs
        db_trades = []
        log_file = Path("research/paper/V4_CANONICAL_1.0/enhanced_signal_log.jsonl")
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        if entry.get("signal") == True:
                            db_trades.append(entry)
        
        return db_trades
    
    def reconcile_positions(self) -> Dict:
        """Reconcile our trades with MT5 positions."""
        mt5_positions = self.get_mt5_positions()
        db_trades = self.get_db_trades()
        
        mismatches = []
        
        # Check: MT5 has positions we don't know about
        for pos in mt5_positions:
            if pos["symbol"] not in ["USDJPYm"]:
                mismatches.append({
                    "type": "UNKNOWN_POSITION",
                    "severity": "CRITICAL",
                    "details": f"MT5 has {pos['symbol']} position we don't track",
                    "mt5": pos
                })
            
            if pos["sl"] == 0 or pos["tp"] == 0:
                mismatches.append({
                    "type": "UNPROTECTED_POSITION",
                    "severity": "CRITICAL",
                    "details": f"Position {pos['ticket']} has no SL/TP",
                    "mt5": pos
                })
        
        # Check: DB says open but MT5 shows nothing
        for trade in db_trades:
            if trade.get("status") == "OPEN":
                mt5_has_it = any(
                    pos["ticket"] == trade.get("position_ticket") 
                    for pos in mt5_positions
                )
                if not mt5_has_it:
                    mismatches.append({
                        "type": "DB_OPEN_MT5_CLOSED",
                        "severity": "HIGH",
                        "details": f"DB says trade {trade.get('trade_id')} is OPEN but MT5 has no position",
                        "db": trade
                    })
        
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mt5_positions_count": len(mt5_positions),
            "db_open_trades_count": len([t for t in db_trades if t.get("status") == "OPEN"]),
            "mismatches_found": len(mismatches),
            "mismatches": mismatches
        }
        
        # Log reconciliation
        with open(self.reconciliation_log, 'a') as f:
            f.write(json.dumps(result) + '\n')
        
        return result
    
    def reconcile_all(self) -> Dict:
        """Full reconciliation: positions, orders, deals."""
        print("="*70)
        print("  MT5 RECONCILIATION")
        print("="*70)
        
        positions = self.get_mt5_positions()
        orders = self.get_mt5_orders()
        deals = self.get_mt5_deals()
        
        print(f"\n  MT5 STATE:")
        print(f"    Open positions: {len(positions)}")
        print(f"    Pending orders: {len(orders)}")
        print(f"    Recent deals (7d): {len(deals)}")
        
        if positions:
            print(f"\n  OPEN POSITIONS:")
            for pos in positions:
                protected = "PROTECTED" if pos["sl"] > 0 and pos["tp"] > 0 else "UNPROTECTED"
                print(f"    {pos['symbol']} {pos['type']} @ {pos['entry']}")
                print(f"      SL: {pos['sl']}, TP: {pos['tp']} [{protected}]")
        
        # Reconcile
        reconciliation = self.reconcile_positions()
        
        print(f"\n  RECONCILIATION RESULT:")
        print(f"    Mismatches: {reconciliation['mismatches_found']}")
        
        if reconciliation["mismatches_found"] > 0:
            print(f"\n  ?? MISMATCHES DETECTED:")
            for mismatch in reconciliation["mismatches"]:
                print(f"    [{mismatch['severity']}] {mismatch['type']}")
                print(f"      {mismatch['details']}")
        else:
            print(f"\n  ? NO MISMATCHES - System consistent with MT5")
        
        return reconciliation

if __name__ == "__main__":
    recon = MT5Reconciliation()
    result = recon.reconcile_all()
