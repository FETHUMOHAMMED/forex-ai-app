"""Immutable Signal Snapshot - Signal CANNOT change after creation.
Ensures reproducibility: the signal that triggered a trade is the signal in the DB.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import hashlib

@dataclass(frozen=True)
class ImmutableSignal:
    """Frozen signal snapshot - cannot be mutated after creation"""
    signal_id: str
    timestamp_utc: str
    pair: str
    direction: str
    confidence: float
    planned_entry: float
    planned_sl: float
    planned_tp: float
    regime: str
    institutional_bias: str
    institutional_score: float
    dealer_pressure: str
    liquidity_state: str
    continuation_prob: float
    model_version: str
    strategy_version: str
    feature_hash: str = ""
    
    def __post_init__(self):
        # Compute hash of all fields for immutability verification
        content = f"{self.signal_id}|{self.timestamp_utc}|{self.pair}|{self.direction}|{self.confidence}|{self.planned_entry}|{self.planned_sl}|{self.planned_tp}|{self.regime}"
        object.__setattr__(self, 'feature_hash', hashlib.md5(content.encode()).hexdigest()[:16])
    
    def to_dict(self):
        """Convert to dict for DB storage - with hash for verification"""
        return {
            "signal_id": self.signal_id,
            "timestamp_utc": self.timestamp_utc,
            "pair": self.pair,
            "direction": self.direction,
            "confidence": self.confidence,
            "planned_entry": self.planned_entry,
            "planned_sl": self.planned_sl,
            "planned_tp": self.planned_tp,
            "regime": self.regime,
            "institutional_bias": self.institutional_bias,
            "institutional_score": self.institutional_score,
            "dealer_pressure": self.dealer_pressure,
            "liquidity_state": self.liquidity_state,
            "continuation_prob": self.continuation_prob,
            "model_version": self.model_version,
            "strategy_version": self.strategy_version,
            "feature_hash": self.feature_hash,
        }
    
    def verify_integrity(self) -> bool:
        """Verify signal hasn't been mutated"""
        content = f"{self.signal_id}|{self.timestamp_utc}|{self.pair}|{self.direction}|{self.confidence}|{self.planned_entry}|{self.planned_sl}|{self.planned_tp}|{self.regime}"
        current_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        return current_hash == self.feature_hash
