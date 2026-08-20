"""Explicit Account Context - Every event carries immutable account identity.
No implicit global 'current_account' state. Every query requires account context.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime, timezone
from enum import Enum

class Environment(str, Enum):
    LIVE_MICRO = "LIVE_MICRO"
    LIVE_MICRO_VALIDATION = "LIVE_MICRO_VALIDATION"
    DEMO = "DEMO"

@dataclass(frozen=True)
class AccountContext:
    """Immutable account identity - CANNOT be changed after creation"""
    account_id: int
    account_name: str
    environment: Environment
    broker_server: str
    
    def __post_init__(self):
        # Validate consistency
        if self.account_name == "Live_Micro" and self.account_id != REDACTED_LIVE_ACCOUNT:
            raise ValueError(f"Live_Micro must have account_id=REDACTED_LIVE_ACCOUNT, got {self.account_id}")
        if self.account_name == "Demo2" and self.account_id != REDACTED_DEMO_ACCOUNT:
            raise ValueError(f"Demo2 must have account_id=REDACTED_DEMO_ACCOUNT, got {self.account_id}")
    
    @property
    def identity_key(self) -> str:
        """Unique identity for queries"""
        return f"{self.account_id}:{self.environment.value}"
    
    def verify_match(self, mt5_account_id: int, mt5_server: str) -> bool:
        """Verify MT5 actual account matches this context"""
        if mt5_account_id != self.account_id:
            print(f"[ACCOUNT MISMATCH] Expected {self.account_id}, MT5 has {mt5_account_id}")
            return False
        if mt5_server != self.broker_server:
            print(f"[SERVER MISMATCH] Expected {self.broker_server}, MT5 has {mt5_server}")
            return False
        return True


# Pre-defined immutable account contexts
LIVE_MICRO_CONTEXT = AccountContext(
    account_id=REDACTED_LIVE_ACCOUNT,
    account_name="Live_Micro",
    environment=Environment.LIVE_MICRO_VALIDATION,
    broker_server="Exness-MT5Real10",
)

DEMO2_CONTEXT = AccountContext(
    account_id=REDACTED_DEMO_ACCOUNT,
    account_name="Demo2",
    environment=Environment.DEMO,
    broker_server="Exness-MT5Trial9",
)


# ============================================================================
# QUERY GUARD - Every DB query must pass account context
# ============================================================================

class QueryGuard:
    """Prevents queries without explicit account context"""
    
    def __init__(self):
        self._queries_without_context = 0
        self._queries_with_context = 0
    
    def require_context(self, account: Optional[AccountContext]) -> AccountContext:
        """HARD CHECK: Query must have account context"""
        if account is None:
            self._queries_without_context += 1
            print(f"[CRITICAL] Query attempted WITHOUT account context!")
            raise ValueError("Account context is REQUIRED for all queries")
        self._queries_with_context += 1
        return account
    
    def get_stats(self):
        return {
            "with_context": self._queries_with_context,
            "without_context": self._queries_without_context,
            "all_queries_have_context": self._queries_without_context == 0,
        }


query_guard = QueryGuard()


# ============================================================================
# TEST
# ============================================================================
if __name__ == "__main__":
    print("=" * 65)
    print("  EXPLICIT ACCOUNT CONTEXT - No Implicit Global State")
    print("=" * 65)
    
    # Test 1: Valid context
    print("\n[1] Query with valid account context:")
    ctx = query_guard.require_context(LIVE_MICRO_CONTEXT)
    print(f"  Context: {ctx.account_name} ({ctx.account_id})")
    print(f"  Environment: {ctx.environment.value}")
    
    # Test 2: No context -> rejected
    print("\n[2] Query WITHOUT account context:")
    try:
        query_guard.require_context(None)
        print("  ERROR: Should have been rejected!")
    except ValueError as e:
        print(f"  CORRECTLY REJECTED: {e}")
    
    # Test 3: Account mismatch detection
    print("\n[3] MT5 actual account mismatch detection:")
    # MT5 says account is Demo2, but context says Live_Micro
    match = LIVE_MICRO_CONTEXT.verify_match(mt5_account_id=REDACTED_DEMO_ACCOUNT, mt5_server="Exness-MT5Trial9")
    print(f"  MT5 has Demo2 (REDACTED_DEMO_ACCOUNT), context is Live_Micro:")
    print(f"  Match: {match}")
    print(f"  Action: {'PROCEED' if match else 'BLOCK TRADE'}")
    
    # Test 4: Valid match
    print("\n[4] Correct account match:")
    match2 = LIVE_MICRO_CONTEXT.verify_match(mt5_account_id=REDACTED_LIVE_ACCOUNT, mt5_server="Exness-MT5Real10")
    print(f"  MT5 has Live_Micro (REDACTED_LIVE_ACCOUNT), context matches:")
    print(f"  Match: {match2}")
    
    print(f"\n{'='*65}")
    print("  STATS:", query_guard.get_stats())
    print("  RESULT: Every query requires explicit account context")
    print(f"{'='*65}")
