"""
Unified TradeSignal - the single data model for all modules.
Replaces scattered dictionaries across the codebase.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

@dataclass
class TradeSignal:
    """One signal to rule them all. Every module uses this."""
    pair: str
    direction: str  # BUY or SELL
    confidence: float
    entry: float
    stop_loss: float
    take_profit: float
    
    # Institutional
    institutional_score: float = 0.0
    institutional_bias: str = "NEUTRAL"
    dealer_pressure: str = "NEUTRAL"
    liquidity_state: str = "NO_EVENT"
    
    # Quality
    quality_grade: str = "F"
    quality_score: float = 0.0
    
    # Context
    regime: str = "UNKNOWN"
    session: str = "UNKNOWN"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Validation
    passed_filters: list = field(default_factory=list)
    rejection_reason: str = ""
    
    @property
    def is_valid(self) -> bool:
        return self.rejection_reason == ""
    
    def reject(self, reason: str):
        self.rejection_reason = reason
    
    def to_dict(self) -> dict:
        return {
            'pair': self.pair, 'signal': self.direction,
            'confidence': self.confidence, 'entry': self.entry,
            'stop_loss': self.stop_loss, 'take_profit': self.take_profit,
            'institutional_score': self.institutional_score,
            'institutional_bias': self.institutional_bias,
            'dealer_pressure': self.dealer_pressure,
            'liquidity_state': self.liquidity_state,
            'grade': self.quality_grade, 'quality_score': self.quality_score,
            'regime': self.institutional_bias, 'session': self.session, 'strength': ('STRONG' if self.confidence >= 0.70 else 'MEDIUM' if self.confidence >= 0.50 else 'WEAK'),
            'timestamp': self.timestamp,
        }
