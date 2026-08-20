"""Automated orphan position detection - finds MT5 positions not in DB"""
import MetaTrader5 as mt5
import sqlite3
from datetime import datetime, timezone

def detect_orphans(db_path="ai-service/trades.db"):
    """Find MT5 positions that are missing from the database"""
    mt5.initialize()
    positions = mt5.positions_get()
    mt5.shutdown()
    
    if not positions:
        return []
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    orphans = []
    for p in positions:
        c.execute("SELECT id FROM trades WHERE ticket = ?", (p.ticket,))
        if not c.fetchone():
            orphans.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "direction": "SELL" if p.type == 1 else "BUY",
                "volume": p.volume,
                "entry": p.price_open,
                "profit": p.profit,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })
    
    conn.close()
    return orphans

if __name__ == "__main__":
    orphans = detect_orphans()
    if orphans:
        print(f"Found {len(orphans)} orphan positions:")
        for o in orphans:
            print(f"  Ticket {o['ticket']}: {o['symbol']} {o['direction']} Vol:{o['volume']} Profit:${o['profit']:.2f}")
    else:
        print("No orphan positions found")
