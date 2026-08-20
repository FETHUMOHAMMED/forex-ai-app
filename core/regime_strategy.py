"""
Regime Strategy V3 - DISTRIBUTING + BREAKOUT edge.
Only trades when specific market conditions align.
"""
from dataclasses import dataclass
from typing import Optional
from shared.trade_signal import TradeSignal

@dataclass
class RegimeStrategy:
    """Production-ready regime filter based on validated edge."""
    
    # Validated configuration (walk-forward PASS)
    allowed_pairs: list = None
    required_structure: list = None
    required_dealer: list = None
    min_confidence: float = 0.55
    min_inst_score: float = 55.0
    
    def __post_init__(self):
        if self.allowed_pairs is None:
            self.allowed_pairs = ['EURUSD']
        if self.required_structure is None:
            self.required_structure = ['BREAKOUT']
        if self.required_dealer is None:
            self.required_dealer = ['DISTRIBUTING']
    
    def validate(self, signal: TradeSignal) -> bool:
        """
        Returns True only if ALL regime conditions are met.
        This is the production gatekeeper.
        """
        # Pair filter
        if signal.pair not in self.allowed_pairs:
            signal.reject(f"Pair {signal.pair} not in allowed list")
            return False
        
        # Structure filter - BREAKOUT only
        if signal.institutional_bias not in self.required_structure:
            signal.reject(f"Structure {signal.institutional_bias} not {self.required_structure}")
            return False
        
        # Dealer filter - DISTRIBUTING only
        if signal.dealer_pressure not in self.required_dealer:
            signal.reject(f"Dealer {signal.dealer_pressure} not {self.required_dealer}")
            return False
        
        # Confidence filter
        if signal.confidence < self.min_confidence:
            signal.reject(f"Confidence {signal.confidence:.3f} < {self.min_confidence}")
            return False
        
        # Institutional score
        if signal.institutional_score < self.min_inst_score:
            signal.reject(f"Inst score {signal.institutional_score:.0f} < {self.min_inst_score}")
            return False
        
        signal.passed_filters = ['pair', 'structure', 'dealer', 'confidence', 'inst_score']
        return True


# Singleton with validated configuration
strategy = RegimeStrategy()

if __name__ == '__main__':
    # Test
    sig = TradeSignal(
        pair='EURUSD', direction='SELL', confidence=0.62,
        entry=1.1000, stop_loss=1.1030, take_profit=1.0940,
        institutional_score=68,
        institutional_bias='BREAKOUT',
        dealer_pressure='DISTRIBUTING',
        liquidity_state='SWEEP_SELL'
    )
    print(f"EURUSD BREAKOUT+DISTRIBUTING: {'PASS' if strategy.validate(sig) else 'FAIL'}")
    
    sig2 = TradeSignal(
        pair='GBPUSD', direction='SELL', confidence=0.62,
        entry=1.3000, stop_loss=1.3030, take_profit=1.2940,
        institutional_score=68,
        institutional_bias='BREAKOUT',
        dealer_pressure='DISTRIBUTING',
        liquidity_state='SWEEP_SELL'
    )
    print(f"GBPUSD BREAKOUT+DISTRIBUTING: {'PASS' if strategy.validate(sig2) else 'FAIL'} - {sig2.rejection_reason}")
    
    sig3 = TradeSignal(
        pair='EURUSD', direction='SELL', confidence=0.62,
        entry=1.1000, stop_loss=1.1030, take_profit=1.0940,
        institutional_score=68,
        institutional_bias='RANGE',
        dealer_pressure='DISTRIBUTING',
        liquidity_state='SWEEP_SELL'
    )
    print(f"EURUSD RANGE+DISTRIBUTING: {'PASS' if strategy.validate(sig3) else 'FAIL'} - {sig3.rejection_reason}")
