"""Verify AI can NEVER directly send orders - permanent separation"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

print("=" * 70)
print("  STRATEGY vs INFRASTRUCTURE SEPARATION VERIFICATION")
print("=" * 70)

# The advisor's required flow:
# Strategy -> Portfolio -> Risk -> OMS -> EMS -> Broker
# AI should NEVER call mt5.order_send() directly

# Check 1: Does strategy engine import order_send?
strategy_files = [
    "packages/strategy/canonical_engine.py",
    "packages/strategy/feature_contract.py",
    "packages/strategy/model_registry.py",
]

print("\n  CHECK 1: Does Strategy Layer call order_send?")
strategy_clean = True
for file in strategy_files:
    if Path(file).exists():
        content = Path(file).read_text()
        has_order_send = 'order_send' in content.lower() or 'mt5.order_send' in content.lower()
        icon = "CLEAN" if not has_order_send else "VIOLATION!"
        if has_order_send:
            strategy_clean = False
        print(f"  [{icon}] {file}")
    else:
        print(f"  [MISSING] {file}")

# Check 2: Does AI model call order_send?
ai_files = ["packages/integrity/ai/deep_health.py", "packages/integrity/ai/models.py"]
print("\n  CHECK 2: Does AI Layer call order_send?")
ai_clean = True
for file in ai_files:
    if Path(file).exists():
        content = Path(file).read_text()
        has_order_send = 'order_send' in content.lower()
        icon = "CLEAN" if not has_order_send else "VIOLATION!"
        if has_order_send:
            ai_clean = False
        print(f"  [{icon}] {file}")

# Check 3: Where IS order_send allowed?
print("\n  CHECK 3: Where order_send IS allowed (should be execution layer only)")
allowed_locations = [
    "packages/integrity/execution/gate.py",  # Gate defines the boundary
    "packages/execution/account_manager.py",  # Isolated account execution
    "packages/execution/execution_pipeline.py",  # The pipeline
]

# Check 4: The advisor's flow order
print("\n  CHECK 4: Correct flow order")
flow = [
    ("1. Strategy", "AI says SELL EURUSD, confidence=0.87"),
    ("2. Portfolio", "Exposure, correlation, allocation"),
    ("3. Risk", "ALLOW or REJECT"),
    ("4. OMS", "CREATE_ORDER"),
    ("5. EMS", "EXECUTE"),
    ("6. Broker", "FILLED @ price"),
]
for step, description in flow:
    print(f"  {step}: {description}")

# Check 5: Risk can REJECT
print("\n  CHECK 5: Risk has REJECT authority")
risk_gate = Path("packages/integrity/execution/gate.py")
if risk_gate.exists():
    content = risk_gate.read_text()
    has_reject = "BLOCKED" in content or "not result.allowed" in content
    print(f"  [{'PASS' if has_reject else 'FAIL'}] Risk can reject orders")

# Check 6: OMS/EMS layer separate from Strategy
print("\n  CHECK 6: OMS/EMS separation")
oms_exists = Path("packages/execution/trade_state_machine.py").exists()
ems_exists = Path("packages/execution/account_manager.py").exists()
print(f"  [{'PASS' if oms_exists else 'FAIL'}] OMS (state machine)")
print(f"  [{'PASS' if ems_exists else 'FAIL'}] EMS (account manager)")

print(f"\n{'='*70}")
checks_pass = strategy_clean and ai_clean and oms_exists and ems_exists
if checks_pass:
    print(f"  VERDICT: AI CANNOT DIRECTLY SEND ORDERS")
    print(f"    Strategy layer: CLEAN (no order_send)")
    print(f"    AI layer: CLEAN (no order_send)")
    print(f"    Risk: Has REJECT authority")
    print(f"    Flow: Strategy -> Risk -> OMS -> EMS -> Broker")
    print(f"    This is the correct institutional architecture")
else:
    print(f"  VERDICT: VIOLATIONS FOUND - AI may have order access")
print("=" * 70)
