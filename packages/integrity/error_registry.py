"""Error Registry - The SYSTEM SAFETY POLICY.
Every error code with severity and required action.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Severity(str, Enum):
    CRITICAL = "CRITICAL"   # HALT trading
    HIGH = "HIGH"           # BLOCK order
    MEDIUM = "MEDIUM"       # DEGRADED (continue with warning)
    LOW = "LOW"             # ALERT only

class Action(str, Enum):
    HALT = "HALT"                   # Stop all trading
    BLOCK_ORDER = "BLOCK_ORDER"     # Block specific order
    BLOCK_AI = "BLOCK_AI"           # Block AI signal
    DEGRADED = "DEGRADED"           # Continue with warning
    ALERT = "ALERT"                 # Notify only

@dataclass(frozen=True)
class ErrorCode:
    """One entry in the safety policy"""
    code: str
    severity: Severity
    action: Action
    description: str

# ============================================================================
# THE SAFETY POLICY - Single source of truth for all error responses
# ============================================================================

ERROR_REGISTRY = {
    # MT5 Errors
    "MT5_DISCONNECTED": ErrorCode("MT5_DISCONNECTED", Severity.CRITICAL, Action.HALT,
                                   "MT5 terminal disconnected"),
    "MT5_AUTH_FAILED": ErrorCode("MT5_AUTH_FAILED", Severity.CRITICAL, Action.HALT,
                                  "MT5 authentication failed"),
    "MT5_ACCOUNT_MISMATCH": ErrorCode("MT5_ACCOUNT_MISMATCH", Severity.CRITICAL, Action.HALT,
                                      "Expected account does not match actual"),
    
    # Database Errors
    "DB_UNAVAILABLE": ErrorCode("DB_UNAVAILABLE", Severity.CRITICAL, Action.HALT,
                                 "Database cannot be accessed"),
    "DB_CORRUPTION": ErrorCode("DB_CORRUPTION", Severity.CRITICAL, Action.HALT,
                                "Database integrity check failed"),
    
    # Risk Errors
    "RISK_UNAVAILABLE": ErrorCode("RISK_UNAVAILABLE", Severity.CRITICAL, Action.HALT,
                                   "Risk calculation unavailable"),
    "RISK_BUDGET_EXCEEDED": ErrorCode("RISK_BUDGET_EXCEEDED", Severity.CRITICAL, Action.BLOCK_ORDER,
                                       "Risk exceeds monetary budget"),
    "RISK_CALCULATION_FAILED": ErrorCode("RISK_CALCULATION_FAILED", Severity.CRITICAL, Action.BLOCK_ORDER,
                                          "Cannot calculate risk"),
    
    # Execution Errors
    "SL_INVALID": ErrorCode("SL_INVALID", Severity.CRITICAL, Action.BLOCK_ORDER,
                             "Stop loss on wrong side of entry"),
    "TP_INVALID": ErrorCode("TP_INVALID", Severity.CRITICAL, Action.BLOCK_ORDER,
                             "Take profit on wrong side of entry"),
    "STALE_SIGNAL": ErrorCode("STALE_SIGNAL", Severity.HIGH, Action.BLOCK_ORDER,
                               "Signal age exceeds freshness threshold"),
    "ENTRY_DEVIATION": ErrorCode("ENTRY_DEVIATION", Severity.HIGH, Action.BLOCK_ORDER,
                                  "Entry price deviates too far from planned"),
    "DUPLICATE_ORDER": ErrorCode("DUPLICATE_ORDER", Severity.HIGH, Action.BLOCK_ORDER,
                                  "Already have position in this direction"),
    "INVALID_VOLUME": ErrorCode("INVALID_VOLUME", Severity.HIGH, Action.BLOCK_ORDER,
                                 "Volume outside broker limits"),
    
    # AI Errors
    "MODEL_LOAD_WARNING": ErrorCode("MODEL_LOAD_WARNING", Severity.HIGH, Action.BLOCK_AI,
                                     "Model failed to load"),
    "INFERENCE_FAILED": ErrorCode("INFERENCE_FAILED", Severity.HIGH, Action.BLOCK_AI,
                                   "Model inference failed"),
    "INVALID_CONFIDENCE": ErrorCode("INVALID_CONFIDENCE", Severity.HIGH, Action.BLOCK_AI,
                                     "Confidence outside [0,1] range"),
    
    # Infrastructure Errors
    "FRONTEND_DOWN": ErrorCode("FRONTEND_DOWN", Severity.MEDIUM, Action.DEGRADED,
                                "Frontend dashboard unavailable"),
    "PROMETHEUS_DOWN": ErrorCode("PROMETHEUS_DOWN", Severity.LOW, Action.ALERT,
                                  "Prometheus metrics unavailable"),
    "API_DOWN": ErrorCode("API_DOWN", Severity.MEDIUM, Action.DEGRADED,
                           "API service unavailable"),
    "HEARTBEAT_STALE": ErrorCode("HEARTBEAT_STALE", Severity.MEDIUM, Action.DEGRADED,
                                  "Trading daemon heartbeat stale"),
    "SCANNER_DEAD": ErrorCode("SCANNER_DEAD", Severity.CRITICAL, Action.HALT,
                               "Integrity scanner stopped running"),
}

def get_error_action(error_code: str) -> Optional[Action]:
    """Get required action for an error code"""
    entry = ERROR_REGISTRY.get(error_code)
    return entry.action if entry else None

def get_error_severity(error_code: str) -> Optional[Severity]:
    """Get severity for an error code"""
    entry = ERROR_REGISTRY.get(error_code)
    return entry.severity if entry else None

def print_safety_policy():
    """Print the complete safety policy"""
    print("=" * 75)
    print("  SYSTEM SAFETY POLICY - ERROR REGISTRY")
    print("=" * 75)
    print(f"\n  {'ERROR CODE':<25} {'SEVERITY':<12} {'ACTION':<15}")
    print(f"  {'-'*55}")
    
    for code, entry in sorted(ERROR_REGISTRY.items()):
        print(f"  {entry.code:<25} {entry.severity.value:<12} {entry.action.value:<15}")
    
    print(f"\n  {'='*55}")
    print(f"  TOTAL ERROR CODES: {len(ERROR_REGISTRY)}")
    print(f"  CRITICAL: {sum(1 for e in ERROR_REGISTRY.values() if e.severity == Severity.CRITICAL)}")
    print(f"  HIGH:     {sum(1 for e in ERROR_REGISTRY.values() if e.severity == Severity.HIGH)}")
    print(f"  MEDIUM:   {sum(1 for e in ERROR_REGISTRY.values() if e.severity == Severity.MEDIUM)}")
    print(f"  LOW:      {sum(1 for e in ERROR_REGISTRY.values() if e.severity == Severity.LOW)}")
    print("=" * 75)

if __name__ == "__main__":
    print_safety_policy()
