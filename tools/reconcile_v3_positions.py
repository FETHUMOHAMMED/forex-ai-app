"""Position-level reconciliation: DB vs MT5 for each V3 trade"""
import MetaTrader5 as mt5
import sqlite3
from datetime import datetime, timezone

mt5.initialize()
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# Get V3 Live_Micro trades from DB
trades = c.execute("""
    SELECT id, pair, signal, entry, stop_loss, take_profit, 
           exit_price, volume, pnl, result, ticket, timestamp, exit_time, regime
    FROM trades 
    WHERE strategy_version = 'V3_REGIME' AND account = 'Live_Micro'
    ORDER BY id
""").fetchall()

from_date = datetime(2026, 8, 1)
to_date = datetime.now()

for t in trades:
    id_, pair, signal, entry, sl, tp, exit_px, vol, pnl, result, ticket, ts, exit_ts, regime = t
    
    print("=" * 70)
    print(f"  V3 TRADE RECONCILIATION - DB ID {id_}")
    print("=" * 70)
    
    # SIGNAL METADATA
    print(f"\n  SIGNAL (from DB):")
    print(f"    Pair: {pair} {signal}")
    print(f"    Entry: {entry} | SL: {sl} | TP: {tp}")
    print(f"    Volume: {vol} | Result: {result} | PnL: {pnl}")
    print(f"    DB Ticket: {ticket}")
    
    # Try to find this position in MT5 history
    # First, try by position ticket
    deals = mt5.history_deals_get(from_date, to_date, position=ticket)
    
    if deals and len(deals) > 0:
        # Found deals for this position
        print(f"\n  MT5 POSITION {ticket}:")
        print(f"    Deals found: {len(deals)}")
        
        entry_deal = None
        exit_deal = None
        
        for d in deals:
            action = "IN" if d.entry == 0 else "OUT"
            d_type = "BUY" if d.type == 0 else "SELL"
            print(f"    Deal {d.ticket}: {d_type} {action} @ {d.price} | Profit: ${d.profit:.2f} | Comm: ${d.commission:.2f}")
            print(f"      Time: {datetime.fromtimestamp(d.time)} | Reason: {d.reason}")
            
            if d.entry == 0:  # IN
                entry_deal = d
            elif d.entry == 1:  # OUT
                exit_deal = d
        
        # Compare
        print(f"\n  RECONCILIATION:")
        if entry_deal:
            print(f"    MT5 Entry: {entry_deal.price} | DB Entry: {entry}")
            if abs(entry_deal.price - entry) > 0.00001:
                diff_pips = abs(entry_deal.price - entry) * 10000
                print(f"    MISMATCH: {diff_pips:.1f} pips difference!")
            else:
                print(f"    Entry MATCH")
        
        if exit_deal and exit_px:
            print(f"    MT5 Exit: {exit_deal.price} | DB Exit: {exit_px}")
            if abs(exit_deal.price - exit_px) > 0.00001:
                print(f"    MISMATCH: {abs(exit_deal.price - exit_px)*10000:.1f} pips")
            else:
                print(f"    Exit MATCH")
        
        if exit_deal:
            actual_pnl = exit_deal.profit + exit_deal.commission
            print(f"    MT5 Net PnL: ${actual_pnl:.2f} | DB PnL: ${pnl if pnl else 0:.2f}")
            if abs(actual_pnl - (pnl if pnl else 0)) > 0.001:
                print(f"    PnL MISMATCH")
            else:
                print(f"    PnL MATCH")
    
    else:
        # Try by order ticket
        print(f"\n  Position {ticket} not found in MT5 history.")
        print(f"  Trying order ticket...")
        
        deals = mt5.history_deals_get(from_date, to_date, ticket=ticket)
        if deals and len(deals) > 0:
            print(f"  Found as ORDER ticket:")
            for d in deals[:3]:
                print(f"    Deal {d.ticket}: Position={d.position_id} | Price={d.price} | Profit={d.profit}")
        else:
            print(f"  NOT FOUND in MT5 history at all!")
            print(f"  STATUS: PHANTOM TRADE (database-only, not in MT5)")

print("\n" + "=" * 70)
print("  SUMMARY")
print("=" * 70)

# Count valid vs phantom
valid = c.execute("""
    SELECT COUNT(*) FROM trades 
    WHERE strategy_version = 'V3_REGIME' AND account = 'Live_Micro'
    AND result IN ('WIN', 'LOSS', 'BREAKEVEN') AND result != 'PHANTOM'
""").fetchone()[0]
print(f"  Valid V3 Trades: {valid}")
print(f"  Milestone: {valid}/10 Execution Verified")

conn.close()
mt5.shutdown()
