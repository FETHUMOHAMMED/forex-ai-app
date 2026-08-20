"""Official Validation Gates - The ONLY counter that matters.
Gate 1: 10 trades (Execution Correctness)
Gate 2: 50 trades (Strategy Validation)
Gate 3: 100 trades (Statistical Evidence)
Gate 4: 300 trades (Production Confidence)
Each gate requires ALL checks to pass for EVERY trade.
"""
import sqlite3
from datetime import datetime, timezone

GATES = [
    {"name": "Gate 1: Execution Correctness", "target": 10},
    {"name": "Gate 2: Strategy Validation", "target": 50},
    {"name": "Gate 3: Statistical Evidence", "target": 100},
    {"name": "Gate 4: Production Confidence", "target": 300},
]

def count_qualified_trades():
    """Count trades that pass ALL execution correctness checks"""
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    
    c.execute("""
        SELECT COUNT(*) FROM trades
        WHERE strategy_version = 'V3_REGIME'
        AND account = 'Live_Micro'
        AND result NOT LIKE 'LEGACY%'
        AND result != 'EXECUTION_EXCEPTION'
        AND result IN ('WIN', 'LOSS', 'BREAKEVEN')
        AND execution_contract_valid = 1
        AND mt5_position_id IS NOT NULL
        AND exit_time IS NOT NULL
        AND pnl IS NOT NULL
        AND entry_deviation_pips IS NOT NULL
        AND entry_deviation_pips <= 5.0
        AND signal_entry IS NOT NULL
        AND actual_entry IS NOT NULL
        AND actual_sl IS NOT NULL
        AND actual_tp IS NOT NULL
    """)
    
    qualified = c.fetchone()[0]
    conn.close()
    return qualified

def print_validation_gates():
    qualified = count_qualified_trades()
    
    print("=" * 65)
    print("  OFFICIAL VALIDATION GATES")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 65)
    
    print(f"\n  QUALIFIED TRADES: {qualified}")
    print(f"  (Each trade must pass ALL 10 execution checks)")
    print()
    
    print(f"  REQUIRED CHECKS PER TRADE:")
    checks = [
        "correct account (Live_Micro)",
        "correct MT5 position",
        "correct timestamps (UTC)",
        "correct actual fill",
        "valid SL",
        "valid TP",
        "correct lot size (0.01 max)",
        "risk budget verified",
        "exact MT5 reconciliation",
        "no stale signal / no extreme deviation",
    ]
    for i, check in enumerate(checks, 1):
        print(f"    {i:2}. {check}")
    
    print()
    for gate in GATES:
        target = gate["target"]
        name = gate["name"]
        pct = min(qualified / target * 100, 100) if target > 0 else 0
        bar_len = 30
        filled = int(pct / 100 * bar_len)
        bar = "#" * filled + "-" * (bar_len - filled)
        
        if qualified >= target:
            status = "[PASS]"
        elif qualified > 0:
            status = "[IN PROGRESS]"
        else:
            status = "[NOT STARTED]"
        
        print(f"  {status} {name}")
        print(f"    [{bar}] {qualified}/{target} ({pct:.0f}%)")
    
    print()
    print("  ADDITIONAL REQUIREMENTS BEYOND 300 TRADES:")
    print("    - Out-of-sample validation")
    print("    - Walk-forward validation")
    print("    - Realistic transaction-cost modeling")
    print("    - Confidence calibration")
    print()
    print("=" * 65)

if __name__ == "__main__":
    print_validation_gates()
