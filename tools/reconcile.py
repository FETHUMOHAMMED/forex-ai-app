"""Trade Reconciliation - Uses proper ticket identity model.
Reconciles DB trades with MT5 using position_ticket (NOT order_ticket).
"""
import sys
sys.path.insert(0, '.')
import MetaTrader5 as mt5
import sqlite3
from datetime import datetime
from packages.execution.mt5_identity import TradeIdentity, TicketType, MT5Ticket

def reconcile_trade(db_id: int) -> TradeIdentity:
    """Reconcile a single DB trade with MT5"""
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM trades WHERE id = ?", (db_id,))
    row = c.fetchone()
    if not row:
        print(f"Trade {db_id} not found in database")
        return None
    
    cols = [d[0] for d in c.description]
    trade = dict(zip(cols, row))
    conn.close()
    
    # Build identity from DB record
    identity = TradeIdentity(
        strategy_trade_id=f"DB_ID_{db_id}",
        signal_id=f"signal_{trade.get('timestamp', 'unknown')}",
        account_id=trade.get('account_id', 0),
        account_name=trade.get('account', 'unknown'),
    )
    
    # The DB 'ticket' field - what type is it?
    db_ticket = trade.get('ticket')
    mt5_position_id = trade.get('mt5_position_id', db_ticket)
    
    print(f"\n{'='*60}")
    print(f"  RECONCILIATION - DB ID {db_id}")
    print(f"{'='*60}")
    print(f"  DB ticket field: {db_ticket}")
    print(f"  DB mt5_position_id: {mt5_position_id}")
    print(f"  DB entry: {trade.get('entry')} | DB exit: {trade.get('exit_price')}")
    print(f"  DB pnl: {trade.get('pnl')} | DB result: {trade.get('result')}")
    
    # Try to find in MT5 by position ID
    mt5.initialize()
    from_date = datetime(2026, 8, 1)
    to_date = datetime.now()
    
    # Only get deals for THIS specific position
    if mt5_position_id:
        deals = mt5.history_deals_get(from_date, to_date, position=mt5_position_id)
    else:
        deals = None
    
    if deals and len(deals) > 0:
        # Filter: only deals belonging to this position
        pos_deals = [d for d in deals if d.position_id == mt5_position_id]
        
        if pos_deals:
            print(f"\n  MT5 Position {mt5_position_id}: {len(pos_deals)} deals")
            
            for d in pos_deals:
                entry_type = "IN" if d.entry == 0 else "OUT"
                print(f"    {entry_type}: Deal#{d.ticket} @ {d.price} | Vol: {d.volume} | Profit: ${d.profit:.2f}")
                
                if d.entry == 0:
                    identity.mt5_entry_deal_ticket = d.ticket
                    identity.actual_entry_price = d.price
                    identity.actual_volume = d.volume
                elif d.entry == 1:
                    identity.mt5_exit_deal_ticket = d.ticket
                    identity.actual_exit_price = d.price
                    identity.mt5_profit = d.profit
                    identity.mt5_commission = d.commission
                    identity.mt5_swap = d.swap
            
            identity.mt5_position_ticket = mt5_position_id
            
            # Compare
            print(f"\n  COMPARISON:")
            print(f"    Entry: DB={trade.get('entry')} vs MT5={identity.actual_entry_price}")
            if trade.get('entry') and identity.actual_entry_price:
                diff = abs(trade['entry'] - identity.actual_entry_price) * 10000
                status = "MATCH" if diff < 0.1 else f"MISMATCH ({diff:.1f} pips)"
                print(f"    Status: {status}")
            
            if trade.get('exit_price') and identity.actual_exit_price:
                print(f"    Exit: DB={trade['exit_price']} vs MT5={identity.actual_exit_price}")
                diff = abs(trade['exit_price'] - identity.actual_exit_price) * 10000
                status = "MATCH" if diff < 0.1 else f"MISMATCH ({diff:.1f} pips)"
                print(f"    Status: {status}")
            
            if trade.get('pnl') is not None and identity.mt5_net_pnl is not None:
                print(f"    PnL: DB=${trade['pnl']:.2f} vs MT5=${identity.mt5_net_pnl:.2f}")
                status = "MATCH" if abs(trade['pnl'] - identity.mt5_net_pnl) < 0.01 else "MISMATCH"
                print(f"    Status: {status}")
            
            return identity
        else:
            print(f"\n  No deals found for position {mt5_position_id}")
            print(f"  All deals returned: {len(deals)} (different positions)")
            for d in deals[:5]:
                print(f"    Deal#{d.ticket} position={d.position_id} entry={d.entry} price={d.price}")
    else:
        print(f"\n  Position {mt5_position_id} NOT FOUND in MT5 history")
        print(f"  Status: PHANTOM or invalid ticket type")
    
    mt5.shutdown()
    return identity


# Run for our V3 trades
for db_id in [146, 162, 163]:
    reconcile_trade(db_id)

print(f"\n{'='*60}")
print("  SUMMARY")
print(f"{'='*60}")
print("  Ticket types MUST be distinguished:")
print("    mt5_order_ticket    - from order_send().order")
print("    mt5_position_ticket - from positions_get()[].ticket")  
print("    mt5_deal_ticket     - from history_deals_get()[].ticket")
print("  These are NOT interchangeable!")
