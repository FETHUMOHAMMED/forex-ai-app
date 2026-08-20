import sqlite3
import MetaTrader5 as mt5

# Check what the DB says is open
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()
c.execute("SELECT id, ticket, pair, signal, volume, pnl, result, account FROM trades WHERE (result IS NULL OR result='' OR result='OPEN') AND strategy_version='V3_REGIME'")
open_trades = c.fetchall()
print("DB Open V3 Trades:")
for t in open_trades:
    print(f"  ID {t[0]}: ticket={t[1]} {t[2]} {t[3]} vol={t[4]} pnl={t[5]} result={t[6]} acct={t[7]}")

# Check MT5 actual positions
mt5.initialize()
positions = mt5.positions_get()
print(f"\nMT5 Actual Positions: {len(positions) if positions else 0}")
if positions:
    for p in positions:
        print(f"  {p.symbol} {'SELL' if p.type==1 else 'BUY'} ticket={p.ticket} vol={p.volume} profit=${p.profit:.2f}")

# Check account info
info = mt5.account_info()
if info:
    print(f"\nMT5 Account: {info.login}")
    print(f"Balance: ${info.balance:.2f}")
    print(f"Equity: ${info.equity:.2f}")
    print(f"Floating PnL: ${info.equity - info.balance:.2f}")

mt5.shutdown()
conn.close()
