"""Event-driven trade ledger - every state change is an event"""
import json
from datetime import datetime, timezone
from pathlib import Path

LEDGER_PATH = Path("ai-service/trade_events.jsonl")

def append_event(event_type: str, trade_id: str, data: dict):
    """Append immutable event to trade ledger"""
    event = {
        "event_type": event_type,
        "trade_id": trade_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")
    return event

def get_events_for_trade(trade_id: str):
    """Get all events for a specific trade"""
    if not LEDGER_PATH.exists():
        return []
    events = []
    with open(LEDGER_PATH) as f:
        for line in f:
            event = json.loads(line)
            if event["trade_id"] == trade_id:
                events.append(event)
    return events
