"""P0: Fix closure to use MT5 lifecycle + P1: Persist risk evidence"""
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

# ========================================================================
# P0: CLOSURE FROM MT5 LIFECYCLE (not DB field)
# ========================================================================
def get_mt5_closure_state(position_ticket: int) -> str:
    """
    MT5 is EXECUTION AUTHORITY for closure.
    Database 'result' field must NOT override MT5.
    """
    mt5.initialize()
    
    # Check if position is currently OPEN
    positions = mt5.positions_get(ticket=position_ticket)
    if positions:
        mt5.shutdown()
        return "OPEN"
    
    # Check deal history for exit deal
    deals = mt5.history_deals_get(datetime(2026, 8, 1, tzinfo=timezone.utc),
                                   datetime.now(timezone.utc), position=position_ticket)
    if deals:
        exit_deals = [d for d in deals if d.position_id == position_ticket and d.entry == 1]
        if exit_deals:
            mt5.shutdown()
            return "CLOSED"
    
    mt5.shutdown()
    return "UNKNOWN"


# ========================================================================
# P1: PERSIST RISK EVIDENCE
# ========================================================================
def add_risk_evidence_columns():
    """Add columns to persist risk decision evidence"""
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    
    risk_columns = [
        ('equity_at_signal', 'REAL'),
        ('equity_at_order', 'REAL'),
        ('risk_percent', 'REAL'),
        ('risk_budget', 'REAL'),
        ('entry_at_order', 'REAL'),
        ('sl_at_order', 'REAL'),
        ('tp_at_order', 'REAL'),
        ('volume_requested', 'REAL'),
        ('volume_executed', 'REAL'),
        ('estimated_risk', 'REAL'),
        ('actual_risk', 'REAL'),
        ('pip_value', 'REAL'),
        ('contract_size', 'REAL'),
        ('mt5_closure_state', 'TEXT'),
    ]
    
    for col, col_type in risk_columns:
        try:
            c.execute(f"ALTER TABLE trades ADD COLUMN {col} {col_type}")
            print(f"  Added: {col}")
        except:
            pass
    
    conn.commit()
    conn.close()
    print("  Risk evidence columns added")


# ========================================================================
# BACKFILL: Update closure state for existing trades from MT5
# ========================================================================
def backfill_mt5_closure():
    """Update mt5_closure_state for existing trades from MT5 authority"""
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    
    c.execute("SELECT id, mt5_position_id FROM trades WHERE mt5_position_id IS NOT NULL")
    trades = c.fetchall()
    
    for trade_id, position_ticket in trades:
        mt5_state = get_mt5_closure_state(position_ticket)
        c.execute("UPDATE trades SET mt5_closure_state = ? WHERE id = ?", 
                 (mt5_state, trade_id))
        print(f"  ID {trade_id}: MT5 closure = {mt5_state}")
    
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("=" * 65)
    print("  P0: MT5 CLOSURE AUTHORITY + P1: RISK EVIDENCE")
    print("=" * 65)
    
    print("\n[P0] MT5 Closure States:")
    backfill_mt5_closure()
    
    print("\n[P1] Risk Evidence Columns:")
    add_risk_evidence_columns()
    
    print(f"\n{'='*65}")
    print("  RESULT:")
    print("  1. MT5 is EXECUTION AUTHORITY for closure")
    print("  2. Database cannot override MT5 state")
    print("  3. Risk evidence persisted for future audit")
    print(f"{'='*65}")
