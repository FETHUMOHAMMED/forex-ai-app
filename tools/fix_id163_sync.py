"""Reconcile ID 163 - closed in MT5 but not in DB"""
import MetaTrader5 as mt5
import sqlite3
from datetime import datetime, timezone

mt5.initialize()

# Check MT5 history for ticket 589584400
from_date = datetime(2026, 8, 10)
to_date = datetime.now()

deals = mt5.history_deals_get(from_date, to_date, position=589584400)
if deals and len(deals) > 0:
    print(f"Found {len(deals)} deals for ticket 589584400:")
    for d in deals:
        print(f"  Deal: {d.ticket} | Type: {d.type} | Entry: {d.entry} | Price: {d.price} | Profit: {d.profit} | Time: {d.time}")
        if d.entry == 1:  # DEAL_ENTRY_OUT (close)
            # Update the DB
            conn = sqlite3.connect('ai-service/trades.db')
            c = conn.cursor()
            close_time = datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat()
            result = 'WIN' if d.profit > 0 else 'LOSS' if d.profit < 0 else 'BREAKEVEN'
            c.execute("""
                UPDATE trades SET 
                    exit_price = ?, exit_time = ?, pnl = ?, result = ?,
                    pnl_percent = CASE WHEN ? != 0 THEN (? / (? * 0.01 * 100000)) * 100 ELSE 0 END
                WHERE ticket = 589584400
            """, (d.price, close_time, d.profit, result, 
                  d.price, d.profit, d.price))
            conn.commit()
            print(f"\n  Updated DB: result={result} pnl={d.profit} exit={d.price} time={close_time}")
            conn.close()
else:
    print("No deals found for ticket 589584400 in MT5 history")
    # Try by position ticket
    history = mt5.history_deals_get(from_date, to_date)
    if history:
        for h in history:
            if h.position_id == 589584400 or h.ticket == 589584400:
                print(f"  Found by position_id: {h.ticket} | Entry: {h.entry} | Price: {h.price} | Profit: {h.profit}")

mt5.shutdown()
