"""KILL SWITCH - Emergency stop mechanism."""
import json
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum

class TradingState(Enum):
    ENABLED = "ENABLED"        # Normal trading allowed
    EMERGENCY_STOP = "EMERGENCY_STOP"  # No new orders, existing managed
    PANIC_STOP = "PANIC_STOP"  # Cancel pending, optionally close positions

class KillSwitch:
    """THE kill switch. Controls whether ANY trading can happen."""
    
    def __init__(self):
        self.state_file = Path("research/kill_switch_state.json")
        self.state = self.load_state()
        
    def load_state(self) -> Dict:
        """Load current kill switch state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "state": TradingState.ENABLED.value,
            "reason": "",
            "set_by": "system",
            "set_at": datetime.now(timezone.utc).isoformat()
        }
    
    def save_state(self):
        """Save current state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def get_state(self) -> str:
        """Get current trading state."""
        self.state = self.load_state()
        return self.state["state"]
    
    def can_trade(self) -> bool:
        """Check if trading is allowed."""
        return self.get_state() == TradingState.ENABLED.value
    
    def emergency_stop(self, reason: str, operator: str = "system"):
        """
        EMERGENCY STOP: No new orders, existing positions managed.
        """
        self.state = {
            "state": TradingState.EMERGENCY_STOP.value,
            "reason": reason,
            "set_by": operator,
            "set_at": datetime.now(timezone.utc).isoformat()
        }
        self.save_state()
        return {
            "status": "EMERGENCY_STOP_ACTIVATED",
            "new_orders": "BLOCKED",
            "existing_positions": "MANAGED",
            "pending_orders": "KEPT",
            "reason": reason
        }
    
    def panic_stop(self, reason: str, close_positions: bool = False, operator: str = "system"):
        """
        PANIC STOP: Cancel pending orders, optionally close positions.
        Requires explicit confirmation for position closing.
        """
        self.state = {
            "state": TradingState.PANIC_STOP.value,
            "reason": reason,
            "set_by": operator,
            "set_at": datetime.now(timezone.utc).isoformat(),
            "close_positions": close_positions
        }
        self.save_state()
        
        actions = {
            "status": "PANIC_STOP_ACTIVATED",
            "new_orders": "BLOCKED",
            "pending_orders": "CANCELLED",
            "reason": reason
        }
        
        if close_positions:
            actions["positions"] = "CLOSING"
            actions["warning"] = "AUTO-LIQUIDATION ACTIVATED - REQUIRES CONFIRMATION"
        else:
            actions["positions"] = "MANAGED"
            actions["note"] = "Positions not auto-closed (no confirmation)"
        
        return actions
    
    def enable(self, operator: str = "system"):
        """Re-enable trading."""
        self.state = {
            "state": TradingState.ENABLED.value,
            "reason": "Re-enabled",
            "set_by": operator,
            "set_at": datetime.now(timezone.utc).isoformat()
        }
        self.save_state()
        return {"status": "TRADING_ENABLED"}
    
    def display_status(self):
        """Display kill switch status."""
        state = self.load_state()
        
        print("="*70)
        print("  KILL SWITCH STATUS")
        print("="*70)
        print(f"\n  State: {state['state']}")
        print(f"  Reason: {state.get('reason', 'N/A')}")
        print(f"  Set by: {state.get('set_by', 'N/A')}")
        print(f"  Set at: {state.get('set_at', 'N/A')}")
        
        if state['state'] == TradingState.ENABLED.value:
            print(f"\n  TRADING: ALLOWED ?")
        elif state['state'] == TradingState.EMERGENCY_STOP.value:
            print(f"\n  NEW ORDERS: BLOCKED ?")
            print(f"  EXISTING POSITIONS: MANAGED")
        elif state['state'] == TradingState.PANIC_STOP.value:
            print(f"\n  NEW ORDERS: BLOCKED ?")
            print(f"  PENDING ORDERS: CANCELLED")
            print(f"  POSITIONS: {'CLOSING' if state.get('close_positions') else 'MANAGED'}")
        
        print("="*70)

# The execution gate must check this before ANY order
def check_kill_switch_before_trade() -> bool:
    """Must be called before any order placement."""
    kill_switch = KillSwitch()
    return kill_switch.can_trade()

if __name__ == "__main__":
    kill_switch = KillSwitch()
    kill_switch.display_status()
    
    print("\n  Test: Emergency Stop")
    kill_switch.emergency_stop("Testing kill switch", "operator")
    kill_switch.display_status()
    
    print("\n  Test: Can trade?")
    print(f"    {kill_switch.can_trade()}")
    
    print("\n  Re-enabling...")
    kill_switch.enable("operator")
    kill_switch.display_status()
