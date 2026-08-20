"""Institutional Order Management System - 12 states, immutable event ledger."""
import json
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, List

class OMSState(str, Enum):
    SIGNAL_CREATED = "SIGNAL_CREATED"
    SIGNAL_APPROVED = "SIGNAL_APPROVED"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACKNOWLEDGED = "ORDER_ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    POSITION_OPEN = "POSITION_OPEN"
    POSITION_MODIFIED = "POSITION_MODIFIED"
    POSITION_CLOSED = "POSITION_CLOSED"
    RECONCILED = "RECONCILED"
    SETTLED = "SETTLED"

# Valid transitions
VALID_TRANSITIONS = {
    OMSState.SIGNAL_CREATED: [OMSState.SIGNAL_APPROVED],
    OMSState.SIGNAL_APPROVED: [OMSState.ORDER_CREATED],
    OMSState.ORDER_CREATED: [OMSState.ORDER_SUBMITTED],
    OMSState.ORDER_SUBMITTED: [OMSState.ORDER_ACKNOWLEDGED],
    OMSState.ORDER_ACKNOWLEDGED: [OMSState.PARTIALLY_FILLED, OMSState.FILLED],
    OMSState.PARTIALLY_FILLED: [OMSState.PARTIALLY_FILLED, OMSState.FILLED],
    OMSState.FILLED: [OMSState.POSITION_OPEN],
    OMSState.POSITION_OPEN: [OMSState.POSITION_MODIFIED, OMSState.POSITION_CLOSED],
    OMSState.POSITION_MODIFIED: [OMSState.POSITION_MODIFIED, OMSState.POSITION_CLOSED],
    OMSState.POSITION_CLOSED: [OMSState.RECONCILED],
    OMSState.RECONCILED: [OMSState.SETTLED],
    OMSState.SETTLED: [],  # Terminal
}

OMS_LEDGER_PATH = Path("ai-service/oms_ledger.jsonl")

class OMSEvent:
    """One state transition in the OMS ledger"""
    def __init__(self, order_id: str, from_state: OMSState, to_state: OMSState,
                 actor: str, account: str, strategy: str,
                 broker_id: str, reason: str, 
                 position_id: Optional[str] = None):
        self.order_id = order_id
        self.from_state = from_state.value
        self.to_state = to_state.value
        self.actor = actor
        self.account = account
        self.strategy = strategy
        self.broker_id = broker_id
        self.reason = reason
        self.position_id = position_id
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor": self.actor,
            "account": self.account,
            "strategy": self.strategy,
            "broker_id": self.broker_id,
            "reason": self.reason,
            "position_id": self.position_id,
            "timestamp": self.timestamp,
        }
    
    def log(self):
        """Append to immutable OMS ledger"""
        OMS_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OMS_LEDGER_PATH, "a") as f:
            f.write(json.dumps(self.to_dict()) + "\n")


class OMS:
    """Order Management System - 12 states with immutable event ledger."""
    
    def __init__(self):
        self.orders: Dict[str, OMSState] = {}
    
    def create_order(self, order_id: str, account: str, strategy: str, 
                     broker_id: str, reason: str) -> bool:
        """Create new order in SIGNAL_CREATED state"""
        if order_id in self.orders:
            return False
        self.orders[order_id] = OMSState.SIGNAL_CREATED
        event = OMSEvent(order_id, OMSState.SIGNAL_CREATED, OMSState.SIGNAL_CREATED,
                        "OMS", account, strategy, broker_id, reason)
        event.log()
        return True
    
    def transition(self, order_id: str, to_state: OMSState, actor: str,
                   account: str, strategy: str, broker_id: str, reason: str,
                   position_id: Optional[str] = None) -> bool:
        """Transition order to new state with full event tracking"""
        if order_id not in self.orders:
            return False
        
        from_state = self.orders[order_id]
        
        # Validate transition
        if to_state not in VALID_TRANSITIONS.get(from_state, []):
            print(f"[OMS] INVALID TRANSITION: {from_state.value} -> {to_state.value}")
            return False
        
        # Record event
        event = OMSEvent(order_id, from_state, to_state, actor, account,
                        strategy, broker_id, reason, position_id)
        event.log()
        
        # Update state
        self.orders[order_id] = to_state
        return True
    
    def get_state(self, order_id: str) -> Optional[OMSState]:
        return self.orders.get(order_id)
    
    def get_order_history(self, order_id: str) -> list:
        """Get complete event history for an order"""
        if not OMS_LEDGER_PATH.exists():
            return []
        events = []
        with open(OMS_LEDGER_PATH) as f:
            for line in f:
                event = json.loads(line)
                if event["order_id"] == order_id:
                    events.append(event)
        return events
    
    def print_order_lifecycle(self, order_id: str):
        """Print complete order lifecycle"""
        events = self.get_order_history(order_id)
        if not events:
            print(f"No events for {order_id}")
            return
        
        print(f"\n{'='*65}")
        print(f"  ORDER LIFECYCLE: {order_id}")
        print(f"{'='*65}")
        for e in events:
            actor = e["actor"]
            transition = f"{e['from_state']} -> {e['to_state']}"
            print(f"  [{e['timestamp'][:19]}] {actor}: {transition}")
            print(f"    Reason: {e['reason']}")
            if e.get('position_id'):
                print(f"    Position: {e['position_id']}")
        print(f"{'='*65}")


if __name__ == "__main__":
    oms = OMS()
    
    # Demonstrate full lifecycle
    order_id = "ORD_20260814_001"
    oms.create_order(order_id, "Live_Micro", "V3_REGIME", "Exness-MT5Real10", "AI signal SELL EURUSD")
    oms.transition(order_id, OMSState.SIGNAL_APPROVED, "STRATEGY_ENGINE", "Live_Micro", "V3_REGIME", "Exness", "Confidence 0.87 passed")
    oms.transition(order_id, OMSState.ORDER_CREATED, "PORTFOLIO_ENGINE", "Live_Micro", "V3_REGIME", "Exness", "Exposure OK")
    oms.transition(order_id, OMSState.ORDER_SUBMITTED, "RISK_ENGINE", "Live_Micro", "V3_REGIME", "Exness", "Risk budget OK")
    oms.transition(order_id, OMSState.ORDER_ACKNOWLEDGED, "EMS", "Live_Micro", "V3_REGIME", "Exness", "MT5 accepted")
    oms.transition(order_id, OMSState.FILLED, "EMS", "Live_Micro", "V3_REGIME", "Exness", "Filled @ 1.15542")
    oms.transition(order_id, OMSState.POSITION_OPEN, "EMS", "Live_Micro", "V3_REGIME", "Exness", "Position verified", position_id="589629837")
    oms.transition(order_id, OMSState.POSITION_CLOSED, "EMS", "Live_Micro", "V3_REGIME", "Exness", "Closed @ 1.15235", position_id="589629837")
    oms.transition(order_id, OMSState.RECONCILED, "RECONCILIATION", "Live_Micro", "V3_REGIME", "Exness", "PnL matched: -$0.13")
    oms.transition(order_id, OMSState.SETTLED, "ACCOUNTING", "Live_Micro", "V3_REGIME", "Exness", "Settled")
    
    oms.print_order_lifecycle(order_id)
    
    # Test invalid transition
    print("\n  Testing invalid transition (SETTLED -> FILLED):")
    result = oms.transition(order_id, OMSState.FILLED, "TEST", "Live_Micro", "V3", "Exness", "Should fail")
    print(f"  Result: {'ALLOWED (WRONG!)' if result else 'REJECTED (correct)'}")
