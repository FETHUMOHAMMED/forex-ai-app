"""HARD ORDER BOUNDARY - Rejects bad orders BEFORE MT5."""
from enum import Enum
from typing import Dict, Tuple
from dataclasses import dataclass
import math

class ValidationStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"

class OrderDirection(Enum):
    """Strictly typed order direction."""
    BUY = "BUY"


@dataclass
class OrderRequest:
    """Raw order from any source."""
    symbol: str
    direction: OrderDirection
    volume: float
    entry: float
    sl: float
    tp: float
    risk_percent: float
    account: str
    strategy_version: str
    account_server: str = "Exness-MT5Real10"
    account_broker: str = "Exness"
    environment: str = "LIVE_MICRO"

class HardOrderBoundary:
    """
    THE FINAL BOUNDARY before MT5.
    Rejects ANY order that doesn't meet ALL criteria.
    Never trusts the strategy layer.
    """
    
    def __init__(self):
        # Hard-coded safety limits (cannot be overridden)
        self.ALLOWED_SYMBOLS = ["USDJPYm"]
        self.ALLOWED_DIRECTIONS = ["BUY"]
        self.ALLOWED_ACCOUNTS = ["REDACTED_LIVE_ACCOUNT"]  # Live_Micro only
        self.MAX_RISK_PERCENT = 0.25
        self.MIN_VOLUME = 0.01
        self.MAX_VOLUME = 1.0
        self.MIN_SL_DISTANCE_PIPS = 10
        self.MAX_SL_DISTANCE_PIPS = 100
        self.MIN_TP_DISTANCE_PIPS = 20  # 2R minimum
        self.MAX_TP_DISTANCE_PIPS = 200  # 2R max (matches 100-pip SL max)
        self.ALLOWED_STRATEGY = "V4_CANONICAL_1.0"
        
    def validate_order(self, order: OrderRequest) -> Tuple[bool, Dict]:
        """
        Validate EVERY field of the order.
        Returns (is_valid, validation_details).
        """
        checks = {}
        
        # 1. Symbol check
        checks["symbol"] = {
            "passed": order.symbol in self.ALLOWED_SYMBOLS,
            "reason": f"Symbol {order.symbol} not allowed" if order.symbol not in self.ALLOWED_SYMBOLS else "OK",
            "value": order.symbol
        }
        
        # 2. Direction check
        # Normalize direction: accept string or enum
        direction_value = order.direction.value if hasattr(order.direction, "value") else str(order.direction).upper().strip()
        checks["direction"] = {
            "passed": direction_value in self.ALLOWED_DIRECTIONS,
            "reason": f"Direction {direction_value} not allowed" if direction_value not in self.ALLOWED_DIRECTIONS else "OK",
            "value": direction_value
        }
        
        # 3. Account check (login + broker + server + environment)
        checks["account_login"] = {
            "passed": order.account in self.ALLOWED_ACCOUNTS,
            "reason": f"Login {order.account} not allowed" if order.account not in self.ALLOWED_ACCOUNTS else "OK",
            "value": order.account
        }
        checks["account_broker"] = {
            "passed": order.account_broker == "Exness",
            "reason": f"Broker {order.account_broker} not allowed" if order.account_broker != "Exness" else "OK",
            "value": order.account_broker
        }
        checks["account_server"] = {
            "passed": order.account_server == "Exness-MT5Real10",
            "reason": f"Server {order.account_server} not allowed" if order.account_server != "Exness-MT5Real10" else "OK",
            "value": order.account_server
        }
        checks["environment"] = {
            "passed": order.environment == "LIVE_MICRO",
            "reason": f"Environment {order.environment} not allowed" if order.environment != "LIVE_MICRO" else "OK",
            "value": order.environment
        }
        
        # 4. Strategy check
        checks["strategy"] = {
            "passed": order.strategy_version == self.ALLOWED_STRATEGY,
            "reason": f"Strategy {order.strategy_version} not allowed" if order.strategy_version != self.ALLOWED_STRATEGY else "OK",
            "value": order.strategy_version
        }
        
        # 5. Risk check
        checks["risk"] = {
            "passed": 0 < order.risk_percent <= self.MAX_RISK_PERCENT,
            "reason": f"Risk {order.risk_percent}% exceeds {self.MAX_RISK_PERCENT}%" if order.risk_percent > self.MAX_RISK_PERCENT else "OK",
            "value": order.risk_percent
        }
        
        # 6. Volume check
        checks["volume"] = {
            "passed": self.MIN_VOLUME <= order.volume <= self.MAX_VOLUME,
            "reason": f"Volume {order.volume} out of range" if not (self.MIN_VOLUME <= order.volume <= self.MAX_VOLUME) else "OK",
            "value": order.volume
        }
        
        # 6.5 Finite number checks (reject NaN/Inf)
        checks["finite_numbers"] = {
            "passed": all([
                math.isfinite(order.entry),
                math.isfinite(order.sl),
                math.isfinite(order.tp),
                math.isfinite(order.volume),
                math.isfinite(order.risk_percent),
            ]),
            "reason": "All numeric fields must be finite" if not all([
                math.isfinite(order.entry),
                math.isfinite(order.sl),
                math.isfinite(order.tp),
                math.isfinite(order.volume),
                math.isfinite(order.risk_percent),
            ]) else "OK",
            "value": "finite"
        }

        # 7. SL check (must be > 0)
        checks["sl_positive"] = {
            "passed": order.sl > 0,
            "reason": "SL must be > 0" if order.sl <= 0 else "OK",
            "value": order.sl
        }
        
        # 8. TP check (must be > 0)
        checks["tp_positive"] = {
            "passed": order.tp > 0,
            "reason": "TP must be > 0" if order.tp <= 0 else "OK",
            "value": order.tp
        }
        
        # 9. SL on correct side (BUY: SL < entry)
        if direction_value == "BUY":
            sl_side_ok = order.sl < order.entry
            checks["sl_side"] = {
                "passed": sl_side_ok,
                "reason": "SL must be below entry for BUY" if not sl_side_ok else "OK",
                "value": f"SL={order.sl}, Entry={order.entry}"
            }
            
            tp_side_ok = order.tp > order.entry
            checks["tp_side"] = {
                "passed": tp_side_ok,
                "reason": "TP must be above entry for BUY" if not tp_side_ok else "OK",
                "value": f"TP={order.tp}, Entry={order.entry}"
            }
        else:
            # SELL (shouldn't happen, but check anyway)
            sl_side_ok = order.sl > order.entry
            checks["sl_side"] = {
                "passed": sl_side_ok,
                "reason": "SL must be above entry for SELL" if not sl_side_ok else "OK",
                "value": f"SL={order.sl}, Entry={order.entry}"
            }
            
            tp_side_ok = order.tp < order.entry
            checks["tp_side"] = {
                "passed": tp_side_ok,
                "reason": "TP must be below entry for SELL" if not tp_side_ok else "OK",
                "value": f"TP={order.tp}, Entry={order.entry}"
            }
        
        # 10. SL distance check (in pips)
        sl_distance_pips = abs(order.entry - order.sl) / 0.01  # Correct pip for 3-digit JPY
        checks["sl_distance"] = {
            "passed": self.MIN_SL_DISTANCE_PIPS <= sl_distance_pips <= self.MAX_SL_DISTANCE_PIPS,
            "reason": f"SL distance {sl_distance_pips:.1f} pips out of range" if not (self.MIN_SL_DISTANCE_PIPS <= sl_distance_pips <= self.MAX_SL_DISTANCE_PIPS) else "OK",
            "value": f"{sl_distance_pips:.1f} pips"
        }
        
        # 11. TP distance check (in pips)
        tp_distance_pips = abs(order.tp - order.entry) / 0.01
        checks["tp_distance"] = {
            "passed": self.MIN_TP_DISTANCE_PIPS <= tp_distance_pips <= self.MAX_TP_DISTANCE_PIPS,
            "reason": f"TP distance {tp_distance_pips:.1f} pips out of range" if not (self.MIN_TP_DISTANCE_PIPS <= tp_distance_pips <= self.MAX_TP_DISTANCE_PIPS) else "OK",
            "value": f"{tp_distance_pips:.1f} pips"
        }

        # Determine overall result
        all_passed = all(check["passed"] for check in checks.values())
        
        return all_passed, checks
    
if __name__ == "__main__":
    boundary = HardOrderBoundary()
    
    print("="*70)
    print("  HARD ORDER BOUNDARY TEST")
    print("="*70)
    
    # TEST 1: Valid order
    print("\n  TEST 1: VALID ORDER")
    valid_order = OrderRequest(
        symbol="USDJPYm",
        direction="BUY",
        volume=0.01,
        entry=154.250,
        sl=153.850,
        tp=155.050,
        risk_percent=0.25,
        account="REDACTED_LIVE_ACCOUNT",
        strategy_version="V4_CANONICAL_1.0"
    )
    is_valid, checks = boundary.validate_order(valid_order)
    print(f"    Result: {'PASS ?' if is_valid else 'FAIL ?'}")
    
    # TEST 2: SL=0, TP=0 (the dangerous case)
    print("\n  TEST 2: UNPROTECTED (SL=0, TP=0)")
    bad_order = OrderRequest(
        symbol="USDJPYm",
        direction="BUY",
        volume=0.01,
        entry=154.250,
        sl=0,
        tp=0,
        risk_percent=0.25,
        account="REDACTED_LIVE_ACCOUNT",
        strategy_version="V4_CANONICAL_1.0"
    )
    is_valid, checks = boundary.validate_order(bad_order)
    print(f"    Result: {'PASS ?' if is_valid else 'FAIL ?'}")
    if not is_valid:
        for name, check in checks.items():
            if not check["passed"]:
                print(f"      FAILED: {name} - {check['reason']}")
    
    # TEST 3: Wrong pair, wrong direction, high risk
    print("\n  TEST 3: WRONG EVERYTHING")
    worst_order = OrderRequest(
        symbol="EURUSDm",
        direction="SELL",
        volume=0.01,
        entry=1.1575,
        sl=0,
        tp=0,
        risk_percent=10.0,
        account="REDACTED_DEMO_ACCOUNT",
        strategy_version="OLD"
    )
    is_valid, checks = boundary.validate_order(worst_order)
    print(f"    Result: {'PASS ?' if is_valid else 'FAIL ?'}")
    if not is_valid:
        failed = [name for name, c in checks.items() if not c["passed"]]
        print(f"    Failed checks: {len(failed)}")
        for name in failed:
            print(f"      - {name}")
    
    # TEST 4: Risk 5% (should fail)
    print("\n  TEST 4: RISK 5% (should fail)")
    risky_order = OrderRequest(
        symbol="USDJPYm",
        direction="BUY",
        volume=0.01,
        entry=154.250,
        sl=153.850,
        tp=155.050,
        risk_percent=5.0,
        account="REDACTED_LIVE_ACCOUNT",
        strategy_version="V4_CANONICAL_1.0"
    )
    is_valid, checks = boundary.validate_order(risky_order)
    print(f"    Result: {'PASS ?' if is_valid else 'FAIL ?'}")
    if not is_valid:
        print(f"      Failed: risk - {checks['risk']['reason']}")








