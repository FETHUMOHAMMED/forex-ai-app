"""
Core Signal Pipeline - The ONE and ONLY signal generation path.
Takes market data, runs through all analyzers, returns TradeSignal.
No MT5, no database, no HTTP - pure logic.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Optional
from shared.trade_signal import TradeSignal


class SignalPipeline:
    """
    Unified signal generation pipeline.
    This is the ONLY place signals are created.
    Daemon, watchdog, and replay all use this.
    """
    
    def __init__(self):
        self._init_analyzers()
    
    def _init_analyzers(self):
        """Lazy-load analyzers to avoid circular imports"""
        from institutional.market_microstructure import MarketMicrostructure
        from institutional.liquidity_intelligence import LiquidityIntelligence
        from institutional.institutional_structure import InstitutionalStructure
        from institutional.market_regime_engine import MarketRegimeEngine
        
        self.microstructure = MarketMicrostructure()
        self.liquidity = LiquidityIntelligence()
        self.structure = InstitutionalStructure()
        self.regime_engine = MarketRegimeEngine()
    
    def generate(self, pair: str, df: pd.DataFrame, 
                 ml_signal: Optional[str] = None,
                 ml_confidence: float = 0.5,
                 ict_buy: bool = False,
                 ict_sell: bool = False) -> TradeSignal:
        """
        Generate a TradeSignal from market data and predictions.
        
        Args:
            pair: Trading pair (e.g., 'EURUSD')
            df: OHLCV DataFrame with 'volume' column
            ml_signal: ML prediction ('BUY', 'SELL', or None)
            ml_confidence: ML confidence (0-1)
            ict_buy: ICT buy confirmation
            ict_sell: ICT sell confirmation
            
        Returns:
            TradeSignal with full institutional context
        """
        # Get current price
        current_price = float(df['close'].iloc[-1])
        
        # Run institutional analyzers
        ms = self.microstructure.analyze(pair, df)
        lq = self.liquidity.analyze(pair, df)
        st = self.structure.analyze(pair, df)
        regime = self.regime_engine.analyze(pair, df, ms, lq, st)
        
        # Determine direction
        direction = None
        if ml_signal and ict_buy and ml_signal == 'BUY':
            direction = 'BUY'
        elif ml_signal and ict_sell and ml_signal == 'SELL':
            direction = 'SELL'
        
        if direction is None:
            signal = TradeSignal(
                pair=pair, direction='NONE', confidence=ml_confidence,
                entry=current_price, stop_loss=0, take_profit=0,
                institutional_score=ms.microstructure_score,
                institutional_bias=ms.institutional_bias,
                dealer_pressure=ms.dealer_pressure,
                liquidity_state=lq.liquidity_state,
                regime=regime.regime
            )
            signal.reject("ML+ICT agreement required")
            return signal
        
        # Calculate SL/TP using ATR
        atr = self._calc_atr(df)
        sl_mult, tp_mult = 2.5, 4.0
        
        if direction == 'BUY':
            sl = current_price - atr * sl_mult
            tp = current_price + atr * tp_mult
        else:
            sl = current_price + atr * sl_mult
            tp = current_price - atr * tp_mult
        
        # Build signal
        signal = TradeSignal(
            pair=pair,
            direction=direction,
            confidence=ml_confidence,
            entry=current_price,
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            institutional_score=ms.microstructure_score,
            institutional_bias=ms.institutional_bias,
            dealer_pressure=ms.dealer_pressure,
            liquidity_state=lq.liquidity_state,
            regime=regime.regime
        )
        
        # Run validation filters
        self._validate(signal)
        
        return signal
    
    def _validate(self, signal: TradeSignal):
        """Apply all validation filters. Reject if any fail."""
        # Filter 1: Institutional score
        if signal.institutional_score < 55:
            signal.reject(f"Inst score {signal.institutional_score:.0f} < 55")
            return
        
        # Filter 2: Dealer pressure
        if signal.dealer_pressure == 'NEUTRAL':
            signal.reject("NEUTRAL dealer pressure")
            return
        
        # Filter 3: Confidence
        if signal.confidence < 0.53:
            signal.reject(f"Confidence {signal.confidence:.3f} < 0.53")
            return
        
        # Filter 4: Liquidity
        if 'NO_EVENT' in str(signal.liquidity_state):
            signal.reject("No liquidity event")
            return
        
        signal.passed_filters = ['inst_score', 'dealer', 'confidence', 'liquidity']
    
    def _calc_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR"""
        high, low, close = df['high'], df['low'], df['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return float(tr.iloc[-period:].mean()) if len(tr) >= period else 0.001


# Quick test
if __name__ == '__main__':
    import MetaTrader5 as mt5
    mt5.initialize()
    mt5.symbol_select('EURUSDm', True)
    rates = mt5.copy_rates_from_pos('EURUSDm', mt5.TIMEFRAME_M15, 0, 200)
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    pipeline = SignalPipeline()
    
    # Test: valid signal
    sig = pipeline.generate('EURUSD', df, ml_signal='SELL', ml_confidence=0.55, ict_buy=False, ict_sell=True)
    print(f"Signal: {sig.direction} conf={sig.confidence:.3f} valid={sig.is_valid}")
    if sig.is_valid:
        print(f"  Entry={sig.entry:.5f} SL={sig.stop_loss:.5f} TP={sig.take_profit:.5f}")
        print(f"  Inst={sig.institutional_score:.0f} Dealer={sig.dealer_pressure} Liq={sig.liquidity_state}")
    else:
        print(f"  Rejected: {sig.rejection_reason}")
    
    # Test: invalid (no ML)
    sig2 = pipeline.generate('EURUSD', df, ml_signal=None, ml_confidence=0.5, ict_buy=False, ict_sell=True)
    print(f"Signal2: valid={sig2.is_valid} reason={sig2.rejection_reason}")
    
    mt5.shutdown()
