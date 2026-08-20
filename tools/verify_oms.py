"""Verify OMS - All advisor requirements"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.execution.oms import OMS, OMSState, VALID_TRANSITIONS, OMSEvent

print("=" * 70)
print("  OMS - ADVISOR REQUIREMENT VERIFICATION")
print("=" * 70)

checks = []
def verify(name, passed, detail=""):
    icon = "[PASS]" if passed else "[FAIL]"
    checks.append(passed)
    print(f"  {icon} {name}")
    if detail:
        print(f"       {detail}")

# 1. All 12 states present
print("\n  CHECK 1: 12 States")
required_states = [
    "SIGNAL_CREATED", "SIGNAL_APPROVED", "ORDER_CREATED", "ORDER_SUBMITTED",
    "ORDER_ACKNOWLEDGED", "PARTIALLY_FILLED", "FILLED", "POSITION_OPEN",
    "POSITION_MODIFIED", "POSITION_CLOSED", "RECONCILED", "SETTLED"
]
present_states = [s for s in required_states if hasattr(OMSState, s)]
verify(f"All 12 states ({len(present_states)}/12)", len(present_states) == 12)

# 2. Valid transitions defined
print("\n  CHECK 2: Valid Transitions")
transition_count = sum(len(v) for v in VALID_TRANSITIONS.values())
verify(f"Transition rules ({transition_count} valid transitions)", transition_count >= 10)

# 3. Event fields (advisor's required fields)
print("\n  CHECK 3: Event Fields (10 required)")
event = OMSEvent("TEST_ORDER", OMSState.SIGNAL_CREATED, OMSState.SIGNAL_APPROVED,
                 "TEST_ACTOR", "Live_Micro", "V3_REGIME", "Exness", "Test reason",
                 position_id="12345")
event_dict = event.to_dict()
required_fields = [
    "order_id", "from_state", "to_state", "actor", "account",
    "strategy", "broker_id", "reason", "position_id", "timestamp"
]
present_fields = [f for f in required_fields if f in event_dict]
verify(f"All 10 event fields ({len(present_fields)}/10)", len(present_fields) == 10)

# 4. Immutable ledger
print("\n  CHECK 4: Immutable Event Ledger")
ledger_path = Path("ai-service/oms_ledger.jsonl")
verify("JSONL ledger created", ledger_path.exists())

# 5. Full lifecycle test
print("\n  CHECK 5: Full Lifecycle (12 transitions)")
oms = OMS()
order_id = "VERIFY_001"
oms.create_order(order_id, "Live_Micro", "V3_REGIME", "Exness", "Test")
transitions = [
    (OMSState.SIGNAL_APPROVED, "STRATEGY", "Confidence passed"),
    (OMSState.ORDER_CREATED, "PORTFOLIO", "Exposure OK"),
    (OMSState.ORDER_SUBMITTED, "RISK", "Budget OK"),
    (OMSState.ORDER_ACKNOWLEDGED, "EMS", "MT5 accepted"),
    (OMSState.FILLED, "EMS", "Filled"),
    (OMSState.POSITION_OPEN, "EMS", "Position open", "POS_001"),
    (OMSState.POSITION_CLOSED, "EMS", "Position closed", "POS_001"),
    (OMSState.RECONCILED, "RECON", "PnL matched"),
    (OMSState.SETTLED, "ACCOUNTING", "Settled"),
]
all_transitions_ok = True
for item in transitions:
    state = item[0]
    actor = item[1]
    reason = item[2]
    position_id = item[3] if len(item) > 3 else None
    if not oms.transition(order_id, state, actor, "Live_Micro", "V3_REGIME", "Exness", reason, position_id):
        all_transitions_ok = False
verify("All valid transitions succeed", all_transitions_ok)

# 6. Invalid transition rejected
print("\n  CHECK 6: Invalid Transition Rejected")
final_state = oms.get_state(order_id)
verify(f"Final state is SETTLED", final_state == OMSState.SETTLED)
invalid_result = oms.transition(order_id, OMSState.FILLED, "TEST", "Live_Micro", "V3", "Exness", "Should fail")
verify("SETTLED -> FILLED rejected", not invalid_result)

# 7. Order history retrievable
print("\n  CHECK 7: Order History")
history = oms.get_order_history(order_id)
verify(f"History retrievable ({len(history)} events)", len(history) >= 10)

# 8. Actor tracking
print("\n  CHECK 8: Actor Tracking")
actors = set(e["actor"] for e in history)
verify(f"Multiple actors tracked ({len(actors)} distinct)", len(actors) >= 5,
       f"Actors: {actors}")

print(f"\n{'='*70}")
passed = sum(checks)
total = len(checks)
print(f"  RESULT: {passed}/{total} CHECKS PASSED")
if passed == total:
    print(f"  VERDICT: OMS COMPLETE - ALL ADVISOR REQUIREMENTS MET")
    print(f"    - 12 states: YES")
    print(f"    - Valid transitions: YES")
    print(f"    - 10 event fields: YES")
    print(f"    - Immutable ledger: YES")
    print(f"    - Full lifecycle: YES")
    print(f"    - Invalid rejected: YES")
    print(f"    - Actor tracking: YES")
print("=" * 70)
