import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta

conn = sqlite3.connect('trades.db')
c = conn.cursor()

mt5.initialize()

now = datetime.now(timezone.utc)
history = mt5.history_deals_get(now - timedelta(days=7), now)

c.execute('SELECT id, pair, entry, volume, timestamp FROM trades WHERE exit_price IS NULL AND pnl IS NULL')
still_open = c.fetchall()
print('Still unmatched: ' + str(len(still_open)))

updated = 0
for t in still_open:
    trade_id, pair, entry, volume, ts = t
    # Make trade_dt timezone-aware
    trade_dt = datetime.fromisoformat(ts)
    if trade_dt.tzinfo is None:
        trade_dt = trade_dt.replace(tzinfo=timezone.utc)
    
    symbol_deals = [d for d in history if d.entry == 1 and d.symbol == (pair + 'm')]
    
    if symbol_deals:
        candidates = []
        for d in symbol_deals:
            deal_time = datetime.fromtimestamp(d.time, tz=timezone.utc)
            diff = abs((deal_time - trade_dt).total_seconds())
            candidates.append((diff, d))
        candidates.sort()
        
        if candidates:
            deal = candidates[0][1]
            pnl_pct = (deal.profit / (entry * volume * 100000)) * 100 if entry and volume else 0
            
            c.execute('''UPDATE trades SET 
                exit_price=?, exit_time=?, pnl=?, pnl_percent=?, result=?
                WHERE id=?''', (
                deal.price,
                datetime.fromtimestamp(deal.time, tz=timezone.utc).isoformat(),
                deal.profit, pnl_pct,
                'WIN' if deal.profit > 0 else 'LOSS', trade_id
            ))
            updated += 1
            print('Matched #' + str(trade_id) + ' ' + pair + ' exit=' + str(round(deal.price, 5)) + ' pnl=' + str(round(deal.profit, 2)))
    else:
        # No matching deal - mark as closed manually with 0 PnL
        print('No deal for #' + str(trade_id) + ' ' + pair + ' - marking as unknown close')

conn.commit()

c.execute('SELECT COUNT(*) FROM trades WHERE exit_price IS NULL AND pnl IS NULL')
remaining = c.fetchone()[0]
print('\nSync complete: ' + str(updated) + ' updated, ' + str(remaining) + ' still open')

c.execute('SELECT COUNT(*), SUM(pnl) FROM trades WHERE pnl IS NOT NULL')
total, net_pnl = c.fetchone()
print('Total closed trades: ' + str(total) + ', Net PnL: ' + str(round(net_pnl, 2) if net_pnl else '0'))

conn.close()
mt5.shutdown()
