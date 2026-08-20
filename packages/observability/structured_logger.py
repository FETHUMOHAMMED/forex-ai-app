
"""Structured JSON logging for production"""
import json
from datetime import datetime, timezone

def log_event(event_type: str, data: dict, level: str = "INFO"):
    """Log structured event as JSON"""
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event_type,
        **data
    }
    print(json.dumps(entry))
    return entry
