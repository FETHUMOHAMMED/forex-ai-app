"""Audit V3 Live_Micro trade sizing and risk"""
import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 60)
print("  V3 Live_Micro - RISK & SIZING AUDIT")
print("=" * 60)

rows = c.execute("""
    SELECT id, pair, signal, entry, stop_loss, exit_price, 
           volume, pnl, result, ticket
    FROM trades 
    WHERE strategy_version = 'V3_REGIME' AND account = 'Live_Micro'
    AND exit_time IS NOT NULL
    ORDER BY id
""").fetchall()

for r in rows:
    id_, pair, signal, entry, sl, exit_px, vol, pnl, result, ticket = r
    
    # Calculate SL distance in pips
    if signal == 'SELL':
        sl_pips = (sl - entry) * 10000 if sl and entry else 0
        move_pips = (entry - exit_px) * 10000 if entry and exit_px else 0
    else:
        sl_pips = (entry - sl) * 10000 if sl and entry else 0
        move_pips = (exit_px - entry) * 10000 if entry and exit_px else 0
    
    # Risk calculation
    notional = entry * vol * 100000 if entry and vol else 0
    risk_if_sl_hit = abs(entry - sl) * vol * 100000 if entry and sl else 0
    
    print(f"\n  ID {id_}: {pair} {signal} | {result} | PnL: ${pnl:.2f}")
    print(f"    Ticket: {ticket}")
    print(f"    Entry: {entry:.5f} | Exit: {exit_px:.5f} | SL: {sl:.5f}")
    print(f"    Volume: {vol} lots | Notional: ${notional:,.0f}")
    print(f"    SL Distance: {sl_pips:.1f} pips | Risk if SL hit: ${risk_if_sl_hit:.2f}")
    print(f"    Actual Move: {move_pips:.1f} pips | Actual Loss: ${pnl:.2f}")
    
    # Compare expected risk (0.05% of $19) vs actual
    expected_risk = 19.06 * 0.0005  # 0.05% of account
    print(f"    Expected risk (0.05%): ${expected_risk:.4f}")
    print(f"    Actual/Expected ratio: {abs(pnl)/expected_risk:.1f}x" if pnl else "")

# Summary
print(f"\n{'='*60}")
print("  SUMMARY")
c.execute("""
    SELECT COUNT(*), COALESCE(SUM(pnl), 0), 
           AVG(volume), AVG(ABS(pnl))
    FROM trades 
    WHERE strategy_version = 'V3_REGIME' AND account = 'Live_Micro'
    AND exit_time IS NOT NULL
""")
s = c.fetchone()
print(f"  Trades: {s[0]}")
print(f"  Total PnL: ${s[1]:.2f}")
print(f"  Avg Volume: {s[2]:.4f} lots" if s[2] else "")
print(f"  Avg |PnL|: ${s[3]:.2f}" if s[3] else "")

conn.close()
