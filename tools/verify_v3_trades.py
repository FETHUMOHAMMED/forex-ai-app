"""Deep verification of V3_REGIME trade data integrity"""
import sqlite3

c = sqlite3.connect('ai-service/trades.db')

print("=" * 70)
print("  V3_REGIME TRADE DATA INTEGRITY CHECK")
print("=" * 70)

# Get all V3 trades with full details
rows = c.execute("""
    SELECT id, pair, signal, entry, stop_loss, take_profit, 
           exit_price, exit_time, pnl, pnl_percent, result,
           volume, ticket, confidence, regime, 
           institutional_bias, institutional_score,
           dealer_pressure, liquidity_state, 
           strategy_version, account, timestamp
    FROM trades 
    WHERE strategy_version = 'V3_REGIME'
    ORDER BY id
""").fetchall()

print(f"\nTotal V3_REGIME trades: {len(rows)}")

for r in rows:
    id_, pair, signal, entry, sl, tp, exit_px, exit_time, pnl, pnl_pct, result, vol, ticket, conf, regime, inst_bias, inst_score, dealer, liq, strategy, account, ts = r
    
    print(f"\n{'='*50}")
    print(f"  TRADE ID {id_}")
    print(f"{'='*50}")
    
    # Basic info
    print(f"  Pair:        {pair}")
    print(f"  Signal:      {signal}")
    print(f"  Account:     {account}")
    print(f"  Strategy:    {strategy}")
    print(f"  Ticket:      {ticket or 'N/A'}")
    print(f"  Volume:      {vol}")
    print(f"  Confidence:  {conf}")
    print(f"  Regime:      {regime}")
    
    # Price data
    print(f"\n  --- Prices ---")
    print(f"  Entry:       {entry}")
    print(f"  Stop Loss:   {sl}")
    print(f"  Take Profit: {tp}")
    print(f"  Exit Price:  {exit_px or 'OPEN'}")
    print(f"  Entry Time:  {ts[:19] if ts else 'N/A'}")
    print(f"  Exit Time:   {exit_time[:19] if exit_time else 'OPEN'}")
    
    # Result
    print(f"\n  --- Result ---")
    print(f"  Result:      {result or 'OPEN'}")
    print(f"  PnL:         {pnl if pnl is not None else 'OPEN'}")
    print(f"  PnL%:        {pnl_pct if pnl_pct is not None else 'OPEN'}")
    
    # Institutional data
    print(f"\n  --- Institutional ---")
    print(f"  Bias:        {inst_bias or 'N/A'}")
    print(f"  Score:       {inst_score or 'N/A'}")
    print(f"  Dealer:      {dealer or 'N/A'}")
    print(f"  Liquidity:   {liq or 'N/A'}")
    
    # Data quality checks
    issues = []
    if ticket is None:
        issues.append("MISSING TICKET")
    if sl is None or sl == 0:
        issues.append("MISSING/INVALID SL")
    if tp is None or tp == 0:
        issues.append("MISSING/INVALID TP")
    if entry is None:
        issues.append("MISSING ENTRY")
    if regime == 'UNKNOWN' or regime is None:
        issues.append("REGIME UNKNOWN")
    if conf is None or conf == 0:
        issues.append("MISSING CONFIDENCE")
    if exit_time and exit_px and pnl is None:
        issues.append("CLOSED BUT NO PNL")
    if account is None:
        issues.append("MISSING ACCOUNT TAG")
    
    if issues:
        print(f"\n  [ISSUES] {', '.join(issues)}")
    else:
        print(f"\n  [OK] Data integrity verified")

# Summary
print(f"\n{'='*70}")
print("  SUMMARY")
print(f"{'='*70}")
total = len(rows)
open_trades = len([r for r in rows if r[9] is None])
closed_trades = total - open_trades
wins = len([r for r in rows if r[10] == 'WIN'])
losses = len([r for r in rows if r[10] == 'LOSS'])
print(f"  Total:      {total}")
print(f"  Open:       {open_trades}")
print(f"  Closed:     {closed_trades}")
print(f"  Wins:       {wins}")
print(f"  Losses:     {losses}")
print(f"  Win Rate:   {(wins/closed_trades*100):.0f}%" if closed_trades > 0 else "  Win Rate:   N/A (no closed trades)")
print(f"{'='*70}")

c.close()
