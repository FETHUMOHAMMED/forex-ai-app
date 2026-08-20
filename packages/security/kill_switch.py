"""Emergency Kill Switch - Immediately halts ALL trading."""
import json
from pathlib import Path
from datetime import datetime, timezone

KILL_SWITCH_FILE = Path("ai-service/kill_switch.json")

def enable_kill_switch(reason: str):
    """Emergency halt - stops ALL trading immediately"""
    data = {
        "enabled": True,
        "reason": reason,
        "activated_at": datetime.now(timezone.utc).isoformat(),
    }
    KILL_SWITCH_FILE.write_text(json.dumps(data, indent=2))
    print(f"[KILL SWITCH] ACTIVATED: {reason}")
    print(f"[KILL SWITCH] ALL TRADING HALTED")

def disable_kill_switch():
    """Resume trading (requires manual authorization)"""
    data = {
        "enabled": False,
        "reason": "",
        "deactivated_at": datetime.now(timezone.utc).isoformat(),
    }
    KILL_SWITCH_FILE.write_text(json.dumps(data, indent=2))
    print(f"[KILL SWITCH] DEACTIVATED - trading authorized")

def is_kill_switch_active() -> bool:
    """Check if trading is halted"""
    if not KILL_SWITCH_FILE.exists():
        return False
    data = json.loads(KILL_SWITCH_FILE.read_text())
    return data.get("enabled", False)

def assert_can_trade():
    """Call before EVERY order. Raises if kill switch active."""
    if is_kill_switch_active():
        reason = json.loads(KILL_SWITCH_FILE.read_text()).get("reason", "Unknown")
        raise TradingHaltedError(f"Kill switch active: {reason}")

class TradingHaltedError(Exception):
    pass
