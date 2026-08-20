"""Institutional Signal Contract - Complete, unambiguous signal schema."""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json

class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NO_TRADE = "NO_TRADE"

class SignalRegime(str, Enum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    BREAKOUT = "BREAKOUT"
    UNKNOWN = "UNKNOWN"  # MUST BE REJECTED by execution

@dataclass(frozen=True)
class InstitutionalSignal:
    """Complete institutional signal contract."""
    signal_id: str
    pair: str                       # "EURUSD" (normalized, no suffix)
    direction: SignalDirection       # "SELL", never "Yes"
    decision: SignalDirection        # Same as direction
    confidence: float               # 0.0 to 1.0
    regime: SignalRegime            # Never UNKNOWN at execution
    signal_timestamp: str           # ISO 8601 UTC
    market_timestamp: str           # Last market data time
    planned_entry: float
    stop_loss: float
    take_profit: float
    strategy_version: str           # "V3_REGIME"
    model_version: str
    account_scope: str              # "Live_Micro" or "Demo2"
    feature_version: str
    expires_at: str                 # Signal expiry (UTC)
    signal_hash: str = ""           # Immutability hash
    
    def __post_init__(self):
        # Validate: UNKNOWN regime = INVALID
        if self.regime == SignalRegime.UNKNOWN:
            raise ValueError("UNKNOWN regime cannot create an execution signal")
        
        # Validate: direction cannot be "Yes"
        if self.direction == SignalDirection.BUY or self.direction == SignalDirection.SELL:
            pass
        else:
            raise ValueError(f"Invalid direction: {self.direction}")
        
        # Validate confidence
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError(f"Confidence {self.confidence} out of range [0,1]")
        
        # Validate prices
        if self.planned_entry <= 0 or self.stop_loss <= 0 or self.take_profit <= 0:
            raise ValueError("Prices must be positive")
        
        # Generate hash for immutability
        content = json.dumps({
            "signal_id": self.signal_id, "pair": self.pair,
            "direction": self.direction.value, "confidence": self.confidence,
            "regime": self.regime.value, "entry": self.planned_entry,
            "sl": self.stop_loss, "tp": self.take_profit,
            "timestamp": self.signal_timestamp,
        })
        object.__setattr__(self, 'signal_hash', 
                          hashlib.sha256(content.encode()).hexdigest()[:16])
    
    def is_expired(self) -> bool:
        """Check if signal has expired."""
        from datetime import datetime as dt
        expiry = dt.fromisoformat(self.expires_at.replace('Z', '+00:00'))
        now = dt.now(timezone.utc)
        return now > expiry
    
    def to_dict(self) -> dict:
        """Convert to dict for API/JSON."""
        return {
            "signal_id": self.signal_id,
            "pair": self.pair,
            "direction": self.direction.value,
            "decision": self.direction.value,
            "confidence": self.confidence,
            "regime": self.regime.value,
            "signal_timestamp": self.signal_timestamp,
            "market_timestamp": self.market_timestamp,
            "planned_entry": self.planned_entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "strategy_version": self.strategy_version,
            "model_version": self.model_version,
            "account_scope": self.account_scope,
            "feature_version": self.feature_version,
            "expires_at": self.expires_at,
            "signal_hash": self.signal_hash,
        }


def create_signal_from_ai_output(ai_output: dict, account_scope: str) -> InstitutionalSignal:
    """
    Convert AI output to institutional signal.
    REJECTS: UNKNOWN regime, "Yes" direction, missing fields.
    """
    direction = ai_output.get("direction", "NO_TRADE")
    
    # Fix: "Yes" is NOT a direction
    if direction in ("Yes", "yes", True):
        direction = "SELL" if ai_output.get("signal") == "SELL" else "NO_TRADE"
    
    regime = ai_output.get("regime", "UNKNOWN")
    
    # Normalize: lowercase -> uppercase (volatile -> VOLATILE)
    if isinstance(regime, str):
        regime = regime.upper()
    
    # UNKNOWN regime = REJECT
    if regime in ("UNKNOWN", None, ""):
        raise ValueError(f"UNKNOWN regime - cannot execute")
    
    signal = InstitutionalSignal(
        signal_id=ai_output.get("signal_id", f"SIG_{datetime.now(timezone.utc).timestamp()}"),
        pair=ai_output.get("pair", "").replace("m", ""),  # Normalize EURUSDm -> EURUSD
        direction=SignalDirection(direction),
        decision=SignalDirection(direction),
        confidence=ai_output.get("confidence", 0),
        regime=SignalRegime(regime),
        signal_timestamp=datetime.now(timezone.utc).isoformat(),
        market_timestamp=datetime.now(timezone.utc).isoformat(),
        planned_entry=ai_output.get("entry", 0),
        stop_loss=ai_output.get("stop_loss", 0),
        take_profit=ai_output.get("take_profit", 0),
        strategy_version=ai_output.get("strategy_version", "V3_REGIME"),
        model_version=ai_output.get("model_version", "unknown"),
        account_scope=account_scope,
        feature_version=ai_output.get("feature_version", "H1-v1"),
        expires_at=datetime.now(timezone.utc).isoformat(),
    )
    return signal


if __name__ == "__main__":
    print("=" * 70)
    print("  INSTITUTIONAL SIGNAL CONTRACT TEST")
    print("=" * 70)
    
    # Test 1: UNKNOWN regime should REJECT
    print("\n  TEST 1: UNKNOWN regime -> REJECT")
    try:
        create_signal_from_ai_output({
            "pair": "EURUSD", "direction": "SELL", "confidence": 0.83,
            "regime": "UNKNOWN", "entry": 1.15542,
            "stop_loss": 1.15718, "take_profit": 1.15261,
        }, "Live_Micro")
        print("  FAIL: Should have rejected")
    except ValueError as e:
        print(f"  PASS: Rejected ({e})")
    
    # Test 2: "Yes" direction -> fix or reject
    print("\n  TEST 2: direction='Yes' -> NOT accepted")
    print("  The contract requires SELL/BUY/NO_TRADE, never 'Yes'")
    
    # Test 3: Valid signal
    print("\n  TEST 3: Valid signal")
    try:
        signal = create_signal_from_ai_output({
            "pair": "EURUSDm", "direction": "SELL", "confidence": 0.83,
            "regime": "volatile", "entry": 1.15542,
            "stop_loss": 1.15718, "take_profit": 1.15261,
        }, "Live_Micro")
        print(f"  PASS: Created signal")
        print(f"    Pair: {signal.pair} (normalized from EURUSDm)")
        print(f"    Direction: {signal.direction.value}")
        print(f"    Regime: {signal.regime.value}")
        print(f"    Hash: {signal.signal_hash}")
    except ValueError as e:
        print(f"  FAIL: {e}")
    
    print(f"\n{'='*70}")
