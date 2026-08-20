"""Clear separation: BLOCKED (good) vs EXECUTION_EXCEPTION (bad)."""
import sqlite3

def classify_outcomes():
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    
    outcomes = {
        "CORRECTLY_BLOCKED": [],      # Safety control worked - NO MT5 position
        "EXECUTION_EXCEPTION": [],    # System defect - trade executed but invalid
        "QUALIFIED": [],              # Passed all checks
    }
    
    c.execute("""
        SELECT id, result, mt5_position_id, execution_contract_valid
        FROM trades WHERE strategy_version='V3_REGIME' AND account='Live_Micro'
        AND result NOT LIKE 'LEGACY%'
    """)
    
    for trade_id, result, mt5_pos, contract_valid in c.fetchall():
        if result == 'EXECUTION_EXCEPTION' and mt5_pos is not None:
            outcomes["EXECUTION_EXCEPTION"].append(trade_id)
        elif result == 'EXECUTION_EXCEPTION' and mt5_pos is None:
            outcomes["CORRECTLY_BLOCKED"].append(trade_id)
        elif result in ('WIN', 'LOSS', 'BREAKEVEN') and contract_valid == 1:
            outcomes["QUALIFIED"].append(trade_id)
    
    conn.close()
    return outcomes

def print_outcome_separation():
    outcomes = classify_outcomes()
    
    print("=" * 70)
    print("  OUTCOME SEPARATION")
    print("=" * 70)
    
    print(f"\n  CORRECTLY BLOCKED (Safety SUCCESS):")
    print(f"    Signal generated -> rejected -> NO MT5 position")
    for tid in outcomes["CORRECTLY_BLOCKED"]:
        print(f"      ID {tid}: BLOCKED before execution")
    if not outcomes["CORRECTLY_BLOCKED"]:
        print(f"      None")
    
    print(f"\n  EXECUTION EXCEPTIONS (System DEFECT):")
    print(f"    Signal generated -> order sent -> malformed execution")
    for tid in outcomes["EXECUTION_EXCEPTION"]:
        print(f"      ID {tid}: EXECUTED but INVALID")
    if not outcomes["EXECUTION_EXCEPTION"]:
        print(f"      None")
    
    print(f"\n  QUALIFIED (Passed all checks):")
    for tid in outcomes["QUALIFIED"]:
        print(f"      ID {tid}: VALID")
    if not outcomes["QUALIFIED"]:
        print(f"      None")
    
    print(f"\n  KEY DISTINCTION:")
    print(f"    BLOCKED = safety worked (GOOD)")
    print(f"    EXCEPTION = system failed (BAD)")
    print(f"    QUALIFIED = valid evidence (TARGET)")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    print_outcome_separation()
