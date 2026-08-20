"""Decision Ledger - Structured rejection codes and immutable decision record."""
import json
from datetime import datetime, timezone
from pathlib import Path

LEDGER_PATH = Path("ai-service/decision_ledger.jsonl")

def record_decision(signal_id: str, strategy_decision: str, strategy_confidence: float,
                    control_decision: str, rejection_codes: list = None,
                    final_decision: str = "NO_TRADE"):
    """Record immutable decision entry in the ledger"""
    entry = {
        "signal_id": signal_id,
        "strategy_decision": strategy_decision,
        "strategy_confidence": strategy_confidence,
        "control_decision": control_decision,
        "rejection_codes": rejection_codes or [],
        "final_decision": final_decision,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def get_decision_ledger(signal_id: str = None):
    """Get decision records - optionally filtered by signal_id"""
    if not LEDGER_PATH.exists():
        return []
    entries = []
    with open(LEDGER_PATH) as f:
        for line in f:
            entry = json.loads(line)
            if signal_id is None or entry["signal_id"] == signal_id:
                entries.append(entry)
    return entries


def aggregate_rejection_codes():
    """Aggregate rejection codes for dashboard"""
    entries = get_decision_ledger()
    codes = {}
    for entry in entries:
        for code in entry.get("rejection_codes", []):
            codes[code] = codes.get(code, 0) + 1
    return codes


if __name__ == "__main__":
    # Record ID 163 decision
    record_decision(
        signal_id="EURUSD_20260810_100616_0001",
        strategy_decision="SELL",
        strategy_confidence=0.83,
        control_decision="REJECT",
        rejection_codes=["STALE_SIGNAL", "ENTRY_DEVIATION", "INVALID_SL"],
        final_decision="NO_TRADE",
    )
    
    print("=" * 60)
    print("  DECISION LEDGER")
    print("=" * 60)
    
    entries = get_decision_ledger()
    for e in entries:
        print(f"\n  Signal: {e['signal_id']}")
        print(f"    Strategy: {e['strategy_decision']} ({e['strategy_confidence']*100:.0f}%)")
        print(f"    Control: {e['control_decision']}")
        print(f"    Rejection Codes: {e['rejection_codes']}")
        print(f"    Final: {e['final_decision']}")
    
    print(f"\n  Aggregated Rejection Codes:")
    for code, count in aggregate_rejection_codes().items():
        print(f"    {code}: {count}")
    print("=" * 60)
