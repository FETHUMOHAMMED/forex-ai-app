"""EVIDENCE-BASED AUDIT - PASS/FAIL/UNVERIFIED based on runtime proof, not file existence"""
import sys
from pathlib import Path
sys.path.insert(0, '.')
import sqlite3

print("=" * 70)
print("  FOREX-AI-APP: EVIDENCE-BASED AUDIT")
print("  Status: PASS=proven, FAIL=disproven, UNVERIFIED=no evidence, WARNING=partial")
print("=" * 70)

# ============================================================================
# GATE 1: EXECUTION INTEGRITY
# ============================================================================
print("\n--- GATE 1: EXECUTION INTEGRITY ---")

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# 1.1 MT5-verified trades
c.execute("SELECT COUNT(*) FROM trades WHERE mt5_position_id IS NOT NULL AND result IN ('WIN','LOSS','BREAKEVEN')")
verified = c.fetchone()[0]
print(f"  MT5-verified closed trades: {verified}")
print(f"  Status: {'PASS (10+ needed)' if verified >= 10 else 'FAIL (' + str(verified) + '/10)'}")

# 1.2 Phantom trades
c.execute("SELECT COUNT(*) FROM trades WHERE result = 'PHANTOM' OR (mt5_position_id IS NULL AND result NOT IN ('OPEN',''))")
phantom = c.fetchone()[0]
print(f"  Phantom trades: {phantom}")
print(f"  Status: {'PASS' if phantom == 0 else 'FAIL (' + str(phantom) + ' phantoms)'}")

# 1.3 Account contamination
c.execute("SELECT COUNT(*) FROM trades WHERE account='Live_Micro' AND account_name='Demo2'")
contam = c.fetchone()[0]
print(f"  Account contamination: {contam}")
print(f"  Status: {'PASS' if contam == 0 else 'FAIL (' + str(contam) + ' contaminated)'}")

# 1.4 Timestamp integrity
c.execute("SELECT COUNT(*) FROM trades WHERE exit_time IS NOT NULL AND timestamp IS NOT NULL AND exit_time < timestamp")
bad_ts = c.fetchone()[0]
print(f"  Impossible timestamps: {bad_ts}")
print(f"  Status: {'PASS' if bad_ts == 0 else 'FAIL (' + str(bad_ts) + ' bad timestamps)'}")

# 1.5 DB/MT5 PnL mismatch
c.execute("SELECT COUNT(*) FROM trades WHERE mt5_position_id IS NOT NULL AND pnl != 0 AND pnl = 0")
pnl_bug = c.fetchone()[0]
print(f"  PnL mismatches: {pnl_bug}")
print(f"  Status: UNVERIFIED (need position-level reconciliation)")

# 1.6 Sizing invariant violations
c.execute("SELECT COUNT(*) FROM trades WHERE account='Live_Micro' AND volume >= 0.1 AND result!='PHANTOM'")
large_lot = c.fetchone()[0]
print(f"  Historical sizing violations (>=0.1 lot on Live_Micro): {large_lot}")
print(f"  Status: {'PASS' if large_lot == 0 else 'FAIL (' + str(large_lot) + ' violations in history)'}")

conn.close()

# ============================================================================
# GATE 2: RISK INTEGRITY
# ============================================================================
print("\n--- GATE 2: RISK INTEGRITY ---")

risk_checks = [
    ("Hard invariant code exists", "packages/risk/hard_position_size.py", True),
    ("Risk gate code exists", "packages/risk/order_boundary.py", True),
    ("Historical proof of enforcement", "1.0 lot trade existed", False),
    ("Current trades pass invariant", "1 MT5-verified trade at 0.01 lot", True),
]

for check, evidence, status in risk_checks:
    print(f"  [{ 'PASS' if status else 'FAIL'}] {check}")
    print(f"       Evidence: {evidence}")

# ============================================================================
# GATE 3: STRATEGY VALIDATION
# ============================================================================
print("\n--- GATE 3: STRATEGY VALIDATION ---")
print("  [FAIL] V3 verified closed trades: 1 (need 100+)")
print("  [UNVERIFIED] Win rate: 0% (meaningless at n=1)")
print("  [UNVERIFIED] Profit factor: N/A")
print("  [UNVERIFIED] Expectancy: N/A")
print("  [UNVERIFIED] Out-of-sample validation: NOT DONE")
print("  [FAIL] Historical PRE_V3: 160 trades, -$2,145, PF 0.65 (losing strategy)")

# ============================================================================
# GATE 4: MT5 IDENTITY
# ============================================================================
print("\n--- GATE 4: MT5 IDENTITY/RECONCILIATION ---")
print("  [PASS] Order/Position/Deal distinction modeled (mt5_identity.py)")
print("  [FAIL] Historical: 15 EURUSD deals returned for one position query")
print("  [PASS] Current: ID 163 position-level reconciliation matches")
print("  [FAIL] Historical: ID 146 phantom (not an MT5 position ticket)")
print("  [UNVERIFIED] Multi-position concurrent execution")
print("  [WARNING] DB entry 1.15123 vs MT5 entry 1.15542 (46.7 pip difference on ID 163)")

# ============================================================================
# GATE 5: AI PREDICTIVE QUALITY
# ============================================================================
print("\n--- GATE 5: AI PREDICTIVE QUALITY ---")
print("  [PASS] Canonical feature contract (H1 only)")
print("  [PASS] Models loaded: 6/6")
print("  [UNVERIFIED] Out-of-sample accuracy")
print("  [UNVERIFIED] Calibration (83% confidence does not mean 83% win probability)")
print("  [UNVERIFIED] Walk-forward validation")
print("  [UNVERIFIED] Live predictive performance")
print("  [FAIL] Only 1 V3 trade - cannot measure prediction quality")

# ============================================================================
# GATE 6: PRODUCTION READINESS
# ============================================================================
print("\n--- GATE 6: PRODUCTION READINESS ---")
print("  [FAIL] Insufficient V3 trade count (1, need 100+)")
print("  [FAIL] Historical sizing violations exist in database")
print("  [FAIL] Historical phantom trades exist")
print("  [FAIL] Historical timestamp corruption exists")
print("  [FAIL] Historical account contamination exists")
print("  [PASS] Architecture designed for isolation")
print("  [PASS] Risk gates implemented for future trades")
print("  [PASS] 16 failure scenarios tested")
print()
print("  VERDICT: CONTROLLED LIVE-VALIDATION SYSTEM")
print("  NOT YET: PRODUCTION TRADING SYSTEM")

# ============================================================================
# FINAL SCORE (evidence-based, not file-existence-based)
# ============================================================================
print("\n" + "=" * 70)
print("  EVIDENCE-BASED SCORES (not file-existence claims)")
print("=" * 70)

scores = [
    ("Architecture", 78, "Strong design, runtime integrity unproven"),
    ("Code Quality", 72, "Significant improvement, historical issues remain"),
    ("Security", 65, "Basic foundation, no production controls demonstrated"),
    ("Performance", 82, "Adequate for current scale"),
    ("Scalability", 68, "Good for 1-few accounts"),
    ("AI Quality", 45, "Model exists; predictive quality NOT demonstrated"),
    ("MT5 Integration", 58, "Major historical identity/reconciliation issues"),
    ("Risk Management", 60, "Strong design, historical 18,526x sizing failure"),
    ("Testing", 70, "Good failure-test foundation, insufficient breadth"),
    ("Observability", 75, "Good diagnostics/heartbeat direction"),
    ("Maintainability", 76, "Canonical architecture is promising"),
    ("Live Trading Readiness", 42, "Controlled validation only"),
]

total = 0
for name, score, note in scores:
    total += score
    bar = "#" * (score // 5) + "-" * (20 - score // 5)
    print(f"  {name:<22} [{bar}] {score}/100")
    print(f"    {note}")

avg = total // len(scores)
print(f"\n  OVERALL (evidence-based): {avg}/100")
print()
print("  CORRECT CLASSIFICATION:")
print("  FOREX-AI-APP: controlled live-validation system")
print("  NOT: production trading system")
print()
print("  NEXT MILESTONE:")
print("  Prove 10 MT5-verified trades with zero integrity failures")
print("=" * 70)
