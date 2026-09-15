"""TIER-2 BOUNDARY - Separate execution environment (NOT a subclass override)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from packages.execution.hard_order_boundary import OrderRequest

class Tier2ExecutionPolicy:
    """
    SEPARATE execution policy for $100 micro-live observation.
    NOT a subclass of HardOrderBoundary.
    Does NOT override production safety limits.
    """
    
    def __init__(self):
        self.TIER = "TIER2_MICRO_LIVE_OBSERVATION"
        self.ALLOWED_SYMBOLS = ["USDJPYm"]
        self.ALLOWED_DIRECTIONS = ["BUY"]
        self.ALLOWED_ACCOUNTS = ["REDACTED_LIVE_ACCOUNT"]
        self.ALLOWED_STRATEGY = "V4_CANONICAL_1.0"
        self.MIN_VOLUME = 0.01
        self.MAX_VOLUME = 1.0
        # Tier-2 specific: Allows higher risk for OBSERVATION only
        self.MAX_RISK_PERCENT = 5.0  # For $100 execution testing ONLY
        self.WARNING = "NOT PRODUCTION - Execution observation only"
        self.PRODUCTION_BOUNDARY = None  # Must reference HardOrderBoundary for live
    
    def validate_observation_order(self, order: OrderRequest):
        """
        Validate for OBSERVATION only.
        This is NOT the production path.
        Production MUST use HardOrderBoundary (0.25%).
        """
        checks = {
            "symbol": order.symbol in self.ALLOWED_SYMBOLS,
            "direction": order.direction in self.ALLOWED_DIRECTIONS,
            "account": order.account in self.ALLOWED_ACCOUNTS,
            "strategy": order.strategy_version == self.ALLOWED_STRATEGY,
            "risk_within_tier2": 0 < order.risk_percent <= self.MAX_RISK_PERCENT,
            "volume": self.MIN_VOLUME <= order.volume <= self.MAX_VOLUME,
            "sl_positive": order.sl > 0,
            "tp_positive": order.tp > 0,
        }
        return all(checks.values()), checks

if __name__ == "__main__":
    policy = Tier2ExecutionPolicy()
    print("="*70)
    print("  TIER-2 EXECUTION POLICY (SEPARATE - Not Production)")
    print("="*70)
    print(f"  Tier: {policy.TIER}")
    print(f"  Warning: {policy.WARNING}")
    print(f"  Max risk (observation only): {policy.MAX_RISK_PERCENT}%")
    print(f"\n  NOTE: Production MUST use HardOrderBoundary (0.25%)")
    print(f"  This policy is for OBSERVATION only.")
    
    order = OrderRequest(
        symbol="USDJPYm",
        direction="BUY",
        volume=0.01,
        entry=154.250,
        sl=154.190,
        tp=154.370,
        risk_percent=3.75,
        account="REDACTED_LIVE_ACCOUNT",
        strategy_version="V4_CANONICAL_1.0"
    )
    
    is_valid, checks = policy.validate_observation_order(order)
    print(f"\n  Observation order valid: {is_valid}")
    for check, passed in checks.items():
        print(f"    {'PASS' if passed else 'FAIL'} {check}")
