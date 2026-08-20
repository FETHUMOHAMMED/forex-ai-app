"""Sync ID 164 - position closed in MT5"""
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

# Get the closed deal from MT5
mt5.initialize()
deals = mt5.history_deals_get(position=589629837)
if deals:
    for d in deals:
        if d.entry == 1:  # OUT deal
            close_price = d.price
            close_time = datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat()
            profit = d.profit
            
            conn = sqlite3.connect('ai-service/trades.db')
            c = conn.cursor()
            c.execute("""
                UPDATE trades SET 
                    exit_price = ?,
                    exit_time = ?,
                    pnl = ?,
                    result = CASE WHEN ? > 0 THEN 'WIN' WHEN ? < 0 THEN 'LOSS' ELSE 'BREAKEVEN' END,
                    reason = 'closed - exchange mode no SL/TP'
                WHERE id = 164
            """, (close_price, close_time, profit, profit, profit))
            conn.commit()
            conn.close()
            
            print(f"ID 164 updated:")
            print(f"  Exit: {close_price}")
            print(f"  Close Time: {close_time}")
            print(f"  PnL: ${profit:.2f}")
            print(f"  Result: {'WIN' if profit > 0 else 'LOSS'}")
            break

mt5.shutdown()
