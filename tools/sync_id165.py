"""Sync ID 165 - position closed in MT5, update DB"""
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

# Get MT5 deal history for this position
mt5.initialize()
deals = mt5.history_deals_get(datetime(2026, 8, 13, tzinfo=timezone.utc), 
                               datetime.now(timezone.utc), position=591215040)

if deals:
    for d in deals:
        if d.position_id == 591215040 and d.entry == 1:  # CLOSE deal
            close_price = d.price
            close_time = datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat()
            profit = d.profit
            result = 'WIN' if profit > 0 else 'LOSS' if profit < 0 else 'BREAKEVEN'
            
            conn = sqlite3.connect('ai-service/trades.db')
            c = conn.cursor()
            c.execute("""
                UPDATE trades SET 
                    exit_price = ?, exit_time = ?, pnl = ?, 
                    result = ?, mt5_closure_state = 'CLOSED'
                WHERE id = 165
            """, (close_price, close_time, profit, result))
            conn.commit()
            conn.close()
            
            print(f"ID 165 synced:")
            print(f"  Exit: {close_price}")
            print(f"  PnL: ${profit:.2f}")
            print(f"  Result: {result}")
            print(f"  MT5 Closure: CLOSED")
            break
else:
    print("No close deal found for position 591215040")
    # Check if position is actually still open
    positions = mt5.positions_get(ticket=591215040)
    if positions:
        print("Position IS still open in MT5")
    else:
        print("Position NOT in MT5 - may need wider date range")

mt5.shutdown()
