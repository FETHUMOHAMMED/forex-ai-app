"""Audit V3 trades against MT5 deal history"""
import MetaTrader5 as mt5
import sqlite3
from datetime import datetime

mt5.initialize()

# Get DB trade data
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

tickets = [3037699202, 589584400]

for ticket in tickets:
    print("=" * 60)
    print(f"  TICKET {ticket}")
    print("=" * 60)
    
    # DB record
    c.execute("""
        SELECT id, pair, signal, entry, stop_loss, exit_price, 
               volume, pnl, result, timestamp, exit_time, regime
        FROM trades WHERE ticket = ?
    """, (ticket,))
    db = c.fetchone()
    
    if db:
        print(f"\n  DATABASE:")
        print(f"    Pair: {db[1]} {db[2]}")
        print(f"    Entry: {db[3]} | Exit: {db[5]} | SL: {db[4]}")
        print(f"    Volume: {db[6]} | PnL: {db[7]} | Result: {db[8]}")
        print(f"    Open: {db[9][:19] if db[9] else 'N/A'}")
        print(f"    Close: {db[10][:19] if db[10] else 'OPEN'}")
        print(f"    Regime: {db[11]}")
    
    # MT5 history for this ticket
    from_date = datetime(2026, 8, 1)
    to_date = datetime.now()
    
    # Get deals by position ticket
    deals = mt5.history_deals_get(from_date, to_date, position=ticket)
    if not deals or len(deals) == 0:
        deals = mt5.history_deals_get(from_date, to_date, ticket=ticket)
    
    if deals and len(deals) > 0:
        print(f"\n  MT5 DEALS ({len(deals)}):")
        total_profit = 0
        total_commission = 0
        total_swap = 0
        
        for d in deals:
            deal_type = "BUY" if d.type == 0 else "SELL" if d.type == 1 else "BALANCE" if d.type == 2 else f"TYPE_{d.type}"
            entry_str = "IN" if d.entry == 0 else "OUT" if d.entry == 1 else f"ENTRY_{d.entry}"
            reason_str = "CLIENT" if d.reason == 0 else "SL" if d.reason == 1 else "TP" if d.reason == 2 else "SO" if d.reason == 3 else f"R_{d.reason}"
            
            print(f"    Deal {d.ticket}: {deal_type} {entry_str}")
            print(f"      Volume: {d.volume} | Price: {d.price}")
            print(f"      Profit: ${d.profit:.2f} | Commission: ${d.commission:.2f} | Swap: ${d.swap:.2f}")
            print(f"      Time: {datetime.fromtimestamp(d.time)}")
            print(f"      Reason: {reason_str} | Position: {d.position_id}")
            
            total_profit += d.profit
            total_commission += d.commission
            total_swap += d.swap
        
        net = total_profit + total_commission + total_swap
        print(f"\n    TOTAL: Profit=${total_profit:.2f} Comm=${total_commission:.2f} Swap=${total_swap:.2f}")
        print(f"    NET: ${net:.2f}")
        
        # Compare DB vs MT5
        if db:
            print(f"\n  DB vs MT5 COMPARISON:")
            print(f"    DB PnL:  ${db[7]:.2f}")
            print(f"    MT5 Net: ${net:.2f}")
            if abs(db[7] - net) > 0.001:
                print(f"    MISMATCH! Difference: ${db[7] - net:.2f}")
            else:
                print(f"    MATCH ?")
    else:
        print(f"\n  No MT5 deals found for ticket {ticket}")
    
    print()

# Summary
print("=" * 60)
print("  RISK AUDIT SUMMARY")
print("=" * 60)
c.execute("""
    SELECT 
        COUNT(*),
        COUNT(DISTINCT CASE WHEN volume >= 1.0 THEN id END) as large_lots,
        COUNT(DISTINCT CASE WHEN volume <= 0.01 THEN id END) as micro_lots
    FROM trades 
    WHERE strategy_version = 'V3_REGIME' AND account = 'Live_Micro'
""")
summary = c.fetchone()
print(f"  Total V3 Live_Micro: {summary[0]}")
print(f"  With >= 1.0 lots: {summary[1]} (DANGEROUS)")
print(f"  With <= 0.01 lots: {summary[2]}")

conn.close()
mt5.shutdown()
