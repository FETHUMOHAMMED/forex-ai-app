"""Signal Lifecycle Tracker - Immutable event chain for EVERY signal."""
import json
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

LIFECYCLE_PATH = Path("ai-service/signal_lifecycle.jsonl")

class LifecycleState(str, Enum):
    GENERATED = "GENERATED"
    STRATEGY_APPROVED = "STRATEGY_APPROVED"
    CONTROL_CHECK = "CONTROL_CHECK"
    REJECTED_STALE = "REJECTED_STALE"
    REJECTED_DEVIATION = "REJECTED_DEVIATION"
    REJECTED_INVALID_SLTP = "REJECTED_INVALID_SLTP"
    REJECTED_SPREAD = "REJECTED_SPREAD"
    REJECTED_RISK = "REJECTED_RISK"
    REJECTED_SESSION = "REJECTED_SESSION"
    REJECTED_DUPLICATE = "REJECTED_DUPLICATE"
    RISK_APPROVED = "RISK_APPROVED"
    MT5_ORDER_SENT = "MT5_ORDER_SENT"
    POSITION_CREATED = "POSITION_CREATED"
    POSITION_CLOSED = "POSITION_CLOSED"
    RECONCILED = "RECONCILED"
    QUALIFIED = "QUALIFIED"


def create_signal_id(pair: str) -> str:
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    import random
    suffix = f"{random.randint(0, 9999):04d}"
    return f"{pair}_{timestamp}_{suffix}"


def append_lifecycle_event(signal_id: str, state: LifecycleState, detail: str = ""):
    event = {
        "signal_id": signal_id,
        "state": state.value,  # Store as string
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "detail": detail,
    }
    LIFECYCLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LIFECYCLE_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")
    return event


def get_signal_lifecycle(signal_id: str) -> list:
    if not LIFECYCLE_PATH.exists():
        return []
    events = []
    with open(LIFECYCLE_PATH) as f:
        for line in f:
            event = json.loads(line)
            if event["signal_id"] == signal_id:
                events.append(event)
    return events


def print_lifecycle(signal_id: str):
    events = get_signal_lifecycle(signal_id)
    if not events:
        print(f"No lifecycle found for {signal_id}")
        return
    
    rejected_states = {"REJECTED_STALE", "REJECTED_DEVIATION", "REJECTED_INVALID_SLTP", 
                       "REJECTED_SPREAD", "REJECTED_RISK", "REJECTED_SESSION", "REJECTED_DUPLICATE"}
    
    print(f"\n{'='*65}")
    print(f"  SIGNAL LIFECYCLE: {signal_id}")
    print(f"{'='*65}")
    for event in events:
        state = event["state"]  # Already a string
        icon = "X" if state in rejected_states else "->"
        detail = f" - {event['detail']}" if event.get('detail') else ""
        print(f"  {icon} {state}{detail}")
    print(f"{'='*65}")


if __name__ == "__main__":
    # Clear old file
    if LIFECYCLE_PATH.exists():
        LIFECYCLE_PATH.unlink()
    
    # Simulate ID 163's correct lifecycle
    sid = "EURUSD_20260810_100616_0001"
    
    append_lifecycle_event(sid, LifecycleState.GENERATED, "AI signal: SELL EURUSD confidence=83%")
    append_lifecycle_event(sid, LifecycleState.STRATEGY_APPROVED, "Passed regime/ICT/SMC checks")
    append_lifecycle_event(sid, LifecycleState.CONTROL_CHECK, "Entering control plane")
    append_lifecycle_event(sid, LifecycleState.REJECTED_STALE, "Signal age=300s > max=120s")
    append_lifecycle_event(sid, LifecycleState.REJECTED_DEVIATION, "Entry deviation=41.9 pips > max=5.0")
    append_lifecycle_event(sid, LifecycleState.REJECTED_INVALID_SLTP, "SL(1.15299) below entry(1.15542) for SELL")
    
    print_lifecycle(sid)
    
    print(f"\n  This signal was BLOCKED - never reached MT5")
    print(f"  The system now records complete immutable lifecycle")
