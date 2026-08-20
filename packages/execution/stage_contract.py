"""Stage Contract - Enforces EVERY stage is completed before the next.
No stage can be silently skipped. Versioned execution contract.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict

class StageStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"  # Should NEVER happen - indicates a bug

class StageName(str, Enum):
    SIGNAL = "SIGNAL"
    FRESHNESS = "FRESHNESS"
    MARKET_STATE = "MARKET_STATE"
    RISK_CALCULATION = "RISK_CALCULATION"
    ORDER_CONSTRUCTION = "ORDER_CONSTRUCTION"
    MT5_SUBMISSION = "MT5_SUBMISSION"
    ACTUAL_FILL = "ACTUAL_FILL"
    POSITION_VERIFICATION = "POSITION_VERIFICATION"
    SLTP_VERIFICATION = "SLTP_VERIFICATION"
    RECONCILIATION = "RECONCILIATION"
    DB_LEDGER = "DB_LEDGER"

# Canonical stage order - no skipping
STAGE_ORDER: List[StageName] = [
    StageName.SIGNAL,
    StageName.FRESHNESS,
    StageName.MARKET_STATE,
    StageName.RISK_CALCULATION,
    StageName.ORDER_CONSTRUCTION,
    StageName.MT5_SUBMISSION,
    StageName.ACTUAL_FILL,
    StageName.POSITION_VERIFICATION,
    StageName.SLTP_VERIFICATION,
    StageName.RECONCILIATION,
    StageName.DB_LEDGER,
]

@dataclass
class StageResult:
    """Result of ONE stage execution"""
    stage: StageName
    status: StageStatus
    detail: str = ""
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class ExecutionContract:
    """Complete execution contract - ALL stages must PASS in order"""
    trade_id: str
    stages: Dict[StageName, StageResult] = field(default_factory=dict)
    
    def record_stage(self, stage: StageName, passed: bool, detail: str = "") -> StageResult:
        """Record stage result - validates stage order"""
        # Check previous stage passed
        stage_index = STAGE_ORDER.index(stage)
        if stage_index > 0:
            prev_stage = STAGE_ORDER[stage_index - 1]
            if prev_stage not in self.stages:
                raise ContractViolationError(f"Stage {stage.value} called before {prev_stage.value}")
            if self.stages[prev_stage].status != StageStatus.PASSED:
                raise ContractViolationError(f"Cannot proceed to {stage.value}: {prev_stage.value} was {self.stages[prev_stage].status.value}")
        
        result = StageResult(
            stage=stage,
            status=StageStatus.PASSED if passed else StageStatus.FAILED,
            detail=detail
        )
        self.stages[stage] = result
        return result
    
    @property
    def is_complete(self) -> bool:
        """All stages recorded and passed"""
        return len(self.stages) == len(STAGE_ORDER) and all(
            s.status == StageStatus.PASSED for s in self.stages.values()
        )
    
    @property
    def current_stage(self) -> Optional[StageName]:
        """Next stage that needs to execute"""
        for stage in STAGE_ORDER:
            if stage not in self.stages:
                return stage
            if self.stages[stage].status == StageStatus.FAILED:
                return None  # Contract failed
        return None  # All stages complete
    
    def summary(self) -> str:
        lines = [f"EXECUTION CONTRACT: {self.trade_id}"]
        for stage in STAGE_ORDER:
            result = self.stages.get(stage)
            if result:
                icon = "PASS" if result.status == StageStatus.PASSED else "FAIL"
                lines.append(f"  [{icon}] {stage.value}: {result.detail}")
            else:
                lines.append(f"  [....] {stage.value}: NOT EXECUTED")
        lines.append(f"  COMPLETE: {self.is_complete}")
        return "\n".join(lines)


class ContractViolationError(Exception):
    """Raised when a stage is skipped or called out of order"""
    pass


# ============================================================================
# TEST
# ============================================================================
if __name__ == "__main__":
    # Valid full execution
    contract = ExecutionContract(trade_id="V3_TEST_001")
    contract.record_stage(StageName.SIGNAL, True, "SELL EURUSD 83%")
    contract.record_stage(StageName.FRESHNESS, True, "10s old")
    contract.record_stage(StageName.MARKET_STATE, True, "spread OK")
    contract.record_stage(StageName.RISK_CALCULATION, True, "$1.60 risk")
    contract.record_stage(StageName.ORDER_CONSTRUCTION, True, "SELL_LIMIT 0.01")
    contract.record_stage(StageName.MT5_SUBMISSION, True, "retcode 10009")
    contract.record_stage(StageName.ACTUAL_FILL, True, "filled @ 1.15590")
    contract.record_stage(StageName.POSITION_VERIFICATION, True, "pos 589629837")
    contract.record_stage(StageName.SLTP_VERIFICATION, True, "SL/TP set")
    contract.record_stage(StageName.RECONCILIATION, True, "PnL matched")
    contract.record_stage(StageName.DB_LEDGER, True, "persisted")
    
    print(contract.summary())
    print(f"\nContract complete: {contract.is_complete}")
    
    # Test: Skip stage - should raise error
    print("\n--- Test: Skip stage (should FAIL) ---")
    contract2 = ExecutionContract(trade_id="V3_TEST_002")
    contract2.record_stage(StageName.SIGNAL, True, "test")
    try:
        contract2.record_stage(StageName.MT5_SUBMISSION, True, "skipped stages!")
        print("ERROR: Should have raised ContractViolationError")
    except ContractViolationError as e:
        print(f"Correctly blocked: {e}")
