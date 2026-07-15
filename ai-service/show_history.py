import sqlite3

conn = sqlite3.connect('trades.db')
c = conn.cursor()

# Live trades
c.execute('SELECT COUNT(*), SUM(pnl), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) FROM trades WHERE pnl IS NOT NULL')
live_t, live_pnl, live_wins = c.fetchone()

# Historical
c.execute('SELECT SUM(trades), SUM(net_pnl) FROM historical_summary')
hist_t, hist_pnl = c.fetchone()

print('=' * 50)
print('  ANALYTICS DATABASE')
print('=' * 50)
print()
print('Live trades in DB:', live_t, '| PnL:', round(live_pnl or 0, 2))
print('Historical (synthetic):', hist_t or 0, '| PnL:', round(hist_pnl or 0, 2))
print()
total_t = (live_t or 0) + (hist_t or 0)
total_pnl = (live_pnl or 0) + (hist_pnl or 0)
print('TOTAL FOR ANALYTICS:', total_t, 'trades | PnL:', round(total_pnl, 2))
conn.close()