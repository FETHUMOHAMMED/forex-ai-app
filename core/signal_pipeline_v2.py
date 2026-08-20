"""
Signal Pipeline V2 - Uses independent institutional detectors.
Combines ML + ICT + Dealer + Liquidity + Structure.
"""
import sys, os, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.trade_signal import TradeSignal
from institutional.dealer_detector import DealerDetector
from institutional.liquidity_detector import LiquidityDetector
from institutional.structure_detector import StructureDetector

class SignalPipelineV2:
    """V2 pipeline with independent institutional detectors."""
    
    def __init__(self):
        self.dealer = DealerDetector()
        self.liquidity = LiquidityDetector()
        self.structure = StructureDetector()
    
    def generate(self, pair: str, df: pd.DataFrame,
                 ml_signal: str = None, ml_confidence: float = 0.5,
                 ict_buy: bool = False, ict_sell: bool = False) -> TradeSignal:
        
        current_price = float(df['close'].iloc[-1])
        
        # Run all 3 detectors
        dealer = self.dealer.analyze(pair, df)
        liquidity = self.liquidity.analyze(pair, df)
        structure = self.structure.analyze(pair, df)
        
        # Combined institutional confidence
        inst_confidence = (dealer.confidence * 0.3 + 
                          liquidity.confidence * 0.35 + 
                          structure.confidence * 0.35)
        
        # ICT conflict check
        if ict_buy and ict_sell:
            sig = TradeSignal(pair=pair, direction='NONE', confidence=ml_confidence,
                            entry=current_price, stop_loss=0, take_profit=0)
            sig.reject('ICT conflict: both buy and sell signals')
            return sig
        
        # Determine direction
        direction = None
        if ml_signal and ict_buy and ml_signal == 'BUY':
            direction = 'BUY'
        elif ml_signal and ict_sell and ml_signal == 'SELL':
            direction = 'SELL'
        
        if direction is None:
            sig = TradeSignal(pair=pair, direction='NONE', confidence=ml_confidence,
                            entry=current_price, stop_loss=0, take_profit=0,
                            institutional_score=inst_confidence,
                            dealer_pressure=dealer.pressure,
                            liquidity_state=liquidity.state,
                            institutional_bias=structure.phase)
            sig.reject("ML+ICT agreement required")
            return sig
        
        # Calculate SL/TP
        atr = self._calc_atr(df)
        sl_mult, tp_mult = 2.5, 4.0
        if direction == 'BUY':
            sl = current_price - atr * sl_mult
            tp = current_price + atr * tp_mult
        else:
            sl = current_price + atr * sl_mult
            tp = current_price - atr * tp_mult
        
        sig = TradeSignal(
            pair=pair, direction=direction, confidence=ml_confidence,
            entry=current_price, stop_loss=round(sl, 5), take_profit=round(tp, 5),
            institutional_score=inst_confidence,
            institutional_bias=structure.phase,
            dealer_pressure=dealer.pressure,
            liquidity_state=liquidity.state
        )
        
        # Validation with V2 thresholds
        self._validate(sig, dealer, liquidity, structure)
        
        return sig
    
    def _validate(self, sig: TradeSignal, dealer, liquidity, structure):
        """V2 validation - uses independent detector results."""
        
        # Filter 1: Directional agreement (ML + Structure)
        if sig.direction == 'SELL' and structure.phase == 'TRENDING_BULL' and structure.confidence > 65:
            sig.reject(f"SELL rejected: strong bullish structure ({structure.confidence:.0f}%)")
            return
        
        if sig.direction == 'BUY' and structure.phase == 'TRENDING_BEAR' and structure.confidence > 65:
            sig.reject(f"BUY rejected: strong bearish structure ({structure.confidence:.0f}%)")
            return
        
        # Filter 2: Require minimum institutional confidence
        if sig.institutional_score < 45:
            sig.reject(f"Institutional confidence {sig.institutional_score:.0f}% < 45%")
            return
        
        # Filter 3: ML confidence
        if sig.confidence < 0.53:
            sig.reject(f"ML confidence {sig.confidence:.3f} < 0.53")
            return
        
        # Filter 4: Liquidity event
        if liquidity.state == 'LOW_LIQUIDITY' and liquidity.confidence < 50:
            sig.reject("No liquidity event")
            return
        
        sig.passed_filters = ['structure', 'institutional', 'confidence', 'liquidity']
    
    def _calc_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high, low, close = df['high'], df['low'], df['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return float(tr.iloc[-period:].mean()) if len(tr) >= period else 0.001


# Test it
if __name__ == '__main__':
    import MetaTrader5 as mt5
    mt5.initialize()
    
    pipeline = SignalPipelineV2()
    
    for pair in ['EURUSD', 'GBPUSD']:
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
        df = pd.DataFrame(rates)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # Test with ML signal
        for ml_sig, ict_b, ict_s in [('SELL', False, True), ('BUY', True, False)]:
            sig = pipeline.generate(pair, df, ml_signal=ml_sig, ml_confidence=0.88, ict_buy=ict_b, ict_sell=ict_s)
            status = "TRADE" if sig.is_valid else "REJECT"
            print(f"\n{pair} {ml_sig}: {status}")
            print(f"  Inst={sig.institutional_score:.0f}% Dealer={sig.dealer_pressure} Liq={sig.liquidity_state} Struct={sig.institutional_bias}")
            if not sig.is_valid:
                print(f"  Reason: {sig.rejection_reason}")
    
    mt5.shutdown()
