"""Runtime Integrity Gate - Prove ONE complete trade lifecycle.
Every stage must preserve identical identity fields.
Any loss or change = FAIL CLOSED.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum

class RuntimeStage(str, Enum):
    MARKET_DATA = "MARKET_DATA"
    FEATURE_GEN = "FEATURE_GEN"
    STRATEGY = "STRATEGY"
    SIGNAL_OBJECT = "SIGNAL_OBJECT"
    API = "API"
    CACHE = "CACHE"
    CONTROL_PLANE = "CONTROL_PLANE"
    RISK_ENGINE = "RISK_ENGINE"
    EXECUTION_CONTRACT = "EXECUTION_CONTRACT"
    MT5_ORDER = "MT5_ORDER"
    MT5_POSITION = "MT5_POSITION"
    MT5_DEALS = "MT5_DEALS"
    DATABASE = "DATABASE"
    RECONCILIATION = "RECONCILIATION"
    DASHBOARD = "DASHBOARD"

@dataclass
class IdentityField:
    """One field that must remain identical across all stages."""
    name: str
    value: any
    source_stage: RuntimeStage
    verified: bool = False

@dataclass
class RuntimeIntegrityResult:
    """Complete runtime integrity check for one trade."""
    trade_id: str
    stages_passed: List[RuntimeStage] = field(default_factory=list)
    stages_failed: List[tuple] = field(default_factory=list)  # (stage, reason)
    identity_fields: Dict[str, any] = field(default_factory=dict)
    is_complete: bool = False
    failure_reason: Optional[str] = None

class RuntimeIntegrityGate:
    """THE runtime gate. Verifies identity preservation across all 15 stages."""
    
    REQUIRED_IDENTITY_FIELDS = [
        "signal_id", "account_id", "account_name", "MT5_login",
        "pair", "direction", "strategy_version", "model_version",
        "entry", "SL", "TP", "volume", "timestamp",
        "position_ticket", "deal_ticket",
    ]
    
    def __init__(self):
        self.result = RuntimeIntegrityResult(trade_id="")
        self.current_stage = None
    
    def start_trade(self, trade_id: str):
        """Start runtime integrity check for one trade."""
        self.result = RuntimeIntegrityResult(trade_id=trade_id)
        self.current_stage = None
        return self
    
    def verify_stage(self, stage: RuntimeStage, identity: dict) -> bool:
        """Verify one stage preserves identity fields."""
        self.current_stage = stage
        
        # Check all required fields present
        missing = [f for f in self.REQUIRED_IDENTITY_FIELDS if f not in identity]
        if missing:
            self.result.stages_failed.append((stage.value, f"Missing fields: {missing}"))
            return False
        
        # Check fields match previous stages
        for field in self.REQUIRED_IDENTITY_FIELDS:
            if field in self.result.identity_fields:
                if self.result.identity_fields[field] != identity[field]:
                    self.result.stages_failed.append(
                        (stage.value, f"Field {field} changed: "
                         f"{self.result.identity_fields[field]} -> {identity[field]}")
                    )
                    return False
            else:
                self.result.identity_fields[field] = identity[field]
        
        self.result.stages_passed.append(stage)
        return True
    
    def verify_complete(self) -> bool:
        """Check if ALL 15 stages passed."""
        all_stages = set(RuntimeStage)
        passed_stages = set(self.result.stages_passed)
        
        if all_stages == passed_stages:
            self.result.is_complete = True
            return True
        
        missing = all_stages - passed_stages
        self.result.failure_reason = f"Missing stages: {missing}"
        return False
    
    def print_report(self):
        """Print complete runtime integrity report."""
        print("=" * 70)
        print(f"  RUNTIME INTEGRITY GATE - Trade {self.result.trade_id}")
        print("=" * 70)
        
        print(f"\n  STAGES COMPLETED: {len(self.result.stages_passed)}/15")
        for stage in RuntimeStage:
            if stage in self.result.stages_passed:
                print(f"    [PASS] {stage.value}")
            elif any(s == stage.value for s, _ in self.result.stages_failed):
                reason = next(r for s, r in self.result.stages_failed if s == stage.value)
                print(f"    [FAIL] {stage.value}: {reason}")
            else:
                print(f"    [....] {stage.value}")
        
        print(f"\n  IDENTITY FIELDS VERIFIED:")
        for field in self.REQUIRED_IDENTITY_FIELDS:
            if field in self.result.identity_fields:
                print(f"    {field}: {self.result.identity_fields[field]}")
            else:
                print(f"    {field}: NOT SET")
        
        print(f"\n  RESULT: {'COMPLETE' if self.result.is_complete else 'INCOMPLETE'}")
        if self.result.failure_reason:
            print(f"  REASON: {self.result.failure_reason}")
        print("=" * 70)


if __name__ == "__main__":
    gate = RuntimeIntegrityGate()
    gate.start_trade("TRADE_001")
    
    # Simulate one complete trade through all 15 stages
    identity = {
        "signal_id": "SIG_001",
        "account_id": REDACTED_LIVE_ACCOUNT,
        "account_name": "Live_Micro",
        "MT5_login": REDACTED_LIVE_ACCOUNT,
        "pair": "EURUSD",
        "direction": "SELL",
        "strategy_version": "V3_REGIME",
        "model_version": "v1.0",
        "entry": 1.15542,
        "SL": 1.15718,
        "TP": 1.15261,
        "volume": 0.01,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "position_ticket": 592780483,
        "deal_ticket": 591026126,
    }
    
    # Verify all 15 stages
    for stage in RuntimeStage:
        gate.verify_stage(stage, identity)
    
    gate.verify_complete()
    gate.print_report()
    
    # Test: field change should FAIL
    print("\n  TESTING FIELD CHANGE DETECTION:")
    gate2 = RuntimeIntegrityGate()
    gate2.start_trade("TRADE_002")
    
    identity1 = identity.copy()
    gate2.verify_stage(RuntimeStage.SIGNAL_OBJECT, identity1)
    
    identity2 = identity.copy()
    identity2["entry"] = 1.16000  # CHANGED!
    result = gate2.verify_stage(RuntimeStage.MT5_ORDER, identity2)
    print(f"  Field change detected: {not result}")
    if not result:
        print(f"  Reason: {gate2.result.stages_failed[-1][1]}")
