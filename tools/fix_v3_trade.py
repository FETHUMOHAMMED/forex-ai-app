"""Fix the single V3_REGIME trade"""
import sys
sys.path.insert(0, '.')
from tools.common import get_db

conn = get_db()
c = conn.cursor()

c.execute("SELECT id, pair, signal, entry, exit_price, volume, pnl, result, regime FROM trades WHERE strategy_version = 'V3_REGIME'")
trade = c.fetchone()

if not trade:
    print("No V3_REGIME trade found")
    conn.close()
    exit()

id_, pair, signal, entry, exit_price, volume, pnl, result, regime = trade

print(f"V3 Trade ID {id_}:")
print(f"  Pair: {pair} {signal}")
print(f"  Entry: {entry} | Exit: {exit_price} | Vol: {volume}")
print(f"  PnL: ${pnl or 0} | Result: {result} | Regime: {regime}")

# Fix regime if UNKNOWN
if regime == 'UNKNOWN' or regime is None:
    c.execute("SELECT DISTINCT regime FROM trades WHERE pair = ? AND regime != 'UNKNOWN' ORDER BY timestamp DESC LIMIT 1", (pair,))
    suggested_regime = c.fetchone()
    new_regime = suggested_regime[0] if suggested_regime else 'volatile'
    c.execute("UPDATE trades SET regime = ? WHERE id = ?", (new_regime, id_))
    print(f"  Regime: UNKNOWN -> {new_regime}")

# Fix result if CLOSED but entry==exit (breakeven)
if result == 'CLOSED' and entry and exit_price and entry == exit_price:
    c.execute("UPDATE trades SET result = 'BREAKEVEN' WHERE id = ?", (id_,))
    print(f"  Result: CLOSED -> BREAKEVEN")

# Calculate PnL if missing
if (pnl == 0 or pnl is None) and entry and exit_price and volume:
    if signal == 'BUY':
        calc_pnl = (exit_price - entry) * volume * 100000
    else:
        calc_pnl = (entry - exit_price) * volume * 100000
    
    if calc_pnl != 0:
        pnl_pct = (calc_pnl / (entry * volume * 100000)) * 100
        new_result = 'WIN' if calc_pnl > 0 else 'LOSS'
        c.execute("UPDATE trades SET pnl = ?, pnl_percent = ?, result = ? WHERE id = ?", 
                  (round(calc_pnl, 2), round(pnl_pct, 4), new_result, id_))
        print(f"  PnL: $0.00 -> ${calc_pnl:.2f} | Result -> {new_result}")

conn.commit()
conn.close()
print("\nFixed! Run V3 strategy review to verify.")
