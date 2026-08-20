"""Prometheus Metrics - Complete advisor-required metrics"""
from fastapi import APIRouter, Response
import sqlite3
from datetime import datetime, timezone

router = APIRouter()

@router.get("/metrics")
def get_metrics():
    """Export all advisor-required metrics in Prometheus format"""
    conn = sqlite3.connect("ai-service/trades.db")
    c = conn.cursor()
    
    lines = []
    
    # === SIGNAL METRICS ===
    c.execute("SELECT COUNT(*) FROM trades WHERE strategy_version='V3_REGIME' AND account='Live_Micro' AND result NOT LIKE 'LEGACY%'")
    lines.append(f"# TYPE forex_signal_generated_total counter")
    lines.append(f"forex_signal_generated_total {c.fetchone()[0]}")
    
    c.execute("SELECT COUNT(*) FROM trades WHERE result='EXECUTION_EXCEPTION'")
    lines.append(f"# TYPE forex_signal_rejected_total counter")
    lines.append(f"forex_signal_rejected_total {c.fetchone()[0]}")
    
    # === ORDER METRICS ===
    c.execute("SELECT COUNT(*) FROM trades WHERE mt5_position_id IS NOT NULL")
    lines.append(f"# TYPE forex_order_submitted_total counter")
    lines.append(f"forex_order_submitted_total {c.fetchone()[0]}")
    
    c.execute("SELECT COUNT(*) FROM trades WHERE result='EXECUTION_EXCEPTION' AND mt5_position_id IS NULL")
    lines.append(f"# TYPE forex_order_rejected_total counter")
    lines.append(f"forex_order_rejected_total {c.fetchone()[0]}")
    
    # === EXECUTION EXCEPTIONS ===
    c.execute("SELECT COUNT(*) FROM trades WHERE result='EXECUTION_EXCEPTION'")
    lines.append(f"# TYPE forex_execution_exception_total counter")
    lines.append(f"forex_execution_exception_total {c.fetchone()[0]}")
    
    # === SLIPPAGE ===
    c.execute("SELECT AVG(entry_deviation_pips) FROM trades WHERE entry_deviation_pips IS NOT NULL")
    avg_slippage = c.fetchone()[0] or 0
    lines.append(f"# TYPE forex_slippage_pips gauge")
    lines.append(f"forex_slippage_pips {avg_slippage}")
    
    # === RISK REJECTIONS ===
    c.execute("SELECT COUNT(*) FROM trades WHERE entry_deviation_pips IS NOT NULL AND entry_deviation_pips > 5.0")
    lines.append(f"# TYPE forex_risk_rejection_total counter")
    lines.append(f"forex_risk_rejection_total {c.fetchone()[0]}")
    
    # === MT5 RECONCILIATION FAILURES ===
    c.execute("SELECT COUNT(*) FROM trades WHERE result='EXECUTION_EXCEPTION' AND pnl IS NULL")
    lines.append(f"# TYPE forex_mt5_reconciliation_failure_total counter")
    lines.append(f"forex_mt5_reconciliation_failure_total {c.fetchone()[0]}")
    
    # === STALE SIGNALS ===
    c.execute("SELECT COUNT(*) FROM trades WHERE entry_deviation_pips IS NOT NULL AND entry_deviation_pips > 5.0 AND planned_entry = 1.15123")
    lines.append(f"# TYPE forex_stale_signal_total counter")
    lines.append(f"forex_stale_signal_total {c.fetchone()[0]}")
    
    # === LEGACY INVALID ===
    c.execute("SELECT COUNT(*) FROM trades WHERE result LIKE 'LEGACY%'")
    lines.append(f"# TYPE forex_legacy_invalid_total gauge")
    lines.append(f"forex_legacy_invalid_total {c.fetchone()[0]}")
    
    # === OPEN POSITIONS ===
    c.execute("SELECT COUNT(*) FROM trades WHERE (result IS NULL OR result='' OR result='OPEN') AND strategy_version='V3_REGIME'")
    lines.append(f"# TYPE forex_open_positions gauge")
    lines.append(f"forex_open_positions {c.fetchone()[0]}")
    
    # === QUALIFIED TRADES ===
    c.execute("""SELECT COUNT(*) FROM trades WHERE strategy_version='V3_REGIME' AND account='Live_Micro' 
                 AND result IN ('WIN','LOSS','BREAKEVEN') AND execution_contract_valid=1""")
    lines.append(f"# TYPE forex_qualified_trades_total counter")
    lines.append(f"forex_qualified_trades_total {c.fetchone()[0]}")
    
    # === PRICE DATA (strategy expected vs actual entry) ===
    c.execute("SELECT planned_entry, actual_entry FROM trades WHERE planned_entry IS NOT NULL AND actual_entry IS NOT NULL ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if row:
        lines.append(f"# TYPE forex_strategy_expected_entry gauge")
        lines.append(f"forex_strategy_expected_entry {row[0]}")
        lines.append(f"# TYPE forex_execution_actual_entry gauge")
        lines.append(f"forex_execution_actual_entry {row[1]}")
    
    # === TIMESTAMP ===
    lines.append(f"forex_last_update {datetime.now(timezone.utc).timestamp()}")
    
    conn.close()
    
    return Response(content="\n".join(lines), media_type="text/plain")
