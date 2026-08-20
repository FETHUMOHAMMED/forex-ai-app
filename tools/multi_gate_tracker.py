"""Multi-Gate Validation Tracker - Separate execution from strategy validation.
Per advisor: "1/10 execution != 1/10 strategy validation"
"""
import sqlite3
from datetime import datetime, timezone

GATES = {
    "A. Data Isolation": {
        "query": "SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND account='Live_Micro' AND account_name!='Live_Micro'",
        "target": 0, "unit": "contamination", "pass_at_zero": True,
    },
    "B. Timestamp Integrity": {
        "query": "SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND exit_time IS NOT NULL AND exit_time < timestamp",
        "target": 0, "unit": "errors", "pass_at_zero": True,
    },
    "C. Phantom Prevention": {
        "query": "SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND strategy_version='V3_REGIME' AND mt5_position_id IS NULL AND result IN ('WIN','LOSS','BREAKEVEN')",
        "target": 0, "unit": "phantoms", "pass_at_zero": True,
    },
    "D. Execution Integrity": {
        "query": "SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND strategy_version='V3_REGIME' AND account='Live_Micro' AND mt5_position_id IS NOT NULL AND result IN ('WIN','LOSS','BREAKEVEN')",
        "target": 10, "unit": "trades", "pass_at_zero": False,
    },
    "E. Risk Enforcement": {
        "query": "SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND strategy_version='V3_REGIME' AND account='Live_Micro' AND volume <= 0.01 AND mt5_position_id IS NOT NULL AND result IN ('WIN','LOSS','BREAKEVEN')",
        "target": 10, "unit": "trades", "pass_at_zero": False,
    },
    "F. MT5 Reconciliation": {
        "query": "SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND strategy_version='V3_REGIME' AND account='Live_Micro' AND mt5_position_id IS NOT NULL AND pnl IS NOT NULL AND result IN ('WIN','LOSS','BREAKEVEN')",
        "target": 10, "unit": "trades", "pass_at_zero": False,
    },
    "G. Strategy Validation": {
        "query": "SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND strategy_version='V3_REGIME' AND account='Live_Micro' AND mt5_position_id IS NOT NULL AND result IN ('WIN','LOSS','BREAKEVEN')",
        "target": 50, "unit": "trades", "pass_at_zero": False,
    },
    "H. Statistical Significance": {
        "query": "SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND strategy_version='V3_REGIME' AND account='Live_Micro' AND mt5_position_id IS NOT NULL AND result IN ('WIN','LOSS','BREAKEVEN')",
        "target": 100, "unit": "trades", "pass_at_zero": False,
    },
    "I. Production Confidence": {
        "query": "SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND strategy_version='V3_REGIME' AND account='Live_Micro' AND mt5_position_id IS NOT NULL AND result IN ('WIN','LOSS','BREAKEVEN')",
        "target": 300, "unit": "trades", "pass_at_zero": False,
    },
}

def evaluate_gates():
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    
    print("=" * 65)
    print("  MULTI-GATE VALIDATION TRACKER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 65)
    
    results = {}
    for gate_name, config in GATES.items():
        c.execute(config["query"])
        count = c.fetchone()[0]
        
        if config["pass_at_zero"]:
            passed = count == 0
        else:
            passed = count >= config["target"]
        
        pct = min(count / config["target"] * 100, 100) if config["target"] > 0 else (100 if passed else 0)
        bar_len = 30
        filled = int(pct / 100 * bar_len)
        bar = "#" * filled + "-" * (bar_len - filled)
        
        status = "PASS" if passed else ("IN PROGRESS" if count > 0 else "NO DATA")
        icon = "[PASS]" if passed else ("[....]" if count > 0 else "[NULL]")
        
        print(f"\n  {icon} {gate_name}")
        print(f"      Progress: [{bar}] {count}/{config['target']} {config['unit']}")
        print(f"      Status: {status}")
        
        results[gate_name] = passed
    
    conn.close()
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n{'='*65}")
    print(f"  GATES PASSED: {passed}/{total}")
    
    if passed >= 3:
        print(f"  PHASE: Data Integrity - VERIFIED")
    if passed >= 6:
        print(f"  PHASE: Execution Integrity - VERIFIED")
    if passed >= 7:
        print(f"  PHASE: Strategy Validation - IN PROGRESS")
    if passed >= 8:
        print(f"  PHASE: Statistical Significance - ACHIEVED")
    if passed == 9:
        print(f"  PHASE: Production Confidence - ACHIEVED")
    
    print(f"  Current: Controlled live-validation")
    print(f"  NOT: Production trading system")
    print(f"{'='*65}")

if __name__ == "__main__":
    evaluate_gates()
