"""
Structure Detector V2 - Independent, explainable.
Detects market structure: trending, ranging, breakout.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class StructureResult:
    phase: str  # TRENDING_BULL, TRENDING_BEAR, RANGE, BREAKOUT
    confidence: float
    swing_structure: str  # HH_HL, LH_LL, MIXED
    details: list

class StructureDetector:
    """Detects market structure with confidence scores."""
    
    def analyze(self, pair: str, df: pd.DataFrame) -> StructureResult:
        details = []
        confidence = 50.0
        
        # 1. Swing structure (HH/HL or LH/LL)
        structure = self._swing_structure(df)
        details.append(f"Swing structure: {structure}")
        
        if structure == "HH_HL":
            confidence += 20
        elif structure == "LH_LL":
            confidence += 20
        else:
            details.append("No clear swing structure")
        
        # 2. Trend strength (ADX-like)
        trend_strength = self._trend_strength(df)
        if trend_strength > 0.3:
            details.append(f"Strong trend: {trend_strength:.2f}")
            confidence += 15
        elif trend_strength > 0.15:
            details.append(f"Moderate trend: {trend_strength:.2f}")
            confidence += 8
        
        # 3. Volatility regime
        vol_state = self._volatility_state(df)
        details.append(f"Volatility: {vol_state}")
        if vol_state == "EXPANDING":
            confidence += 10
        elif vol_state == "CONTRACTING":
            confidence -= 5
        
        confidence = min(100, max(0, confidence))
        
        # Determine phase
        if structure == "HH_HL" and trend_strength > 0.15:
            phase = "TRENDING_BULL"
        elif structure == "LH_LL" and trend_strength > 0.15:
            phase = "TRENDING_BEAR"
        elif vol_state == "EXPANDING":
            phase = "BREAKOUT"
        else:
            phase = "RANGE"
        
        return StructureResult(
            phase=phase,
            confidence=confidence,
            swing_structure=structure,
            details=details
        )
    
    def _swing_structure(self, df: pd.DataFrame) -> str:
        highs = df['high'].values
        lows = df['low'].values
        swing_highs = []
        swing_lows = []
        
        for i in range(5, len(df)-5):
            if highs[i] == max(highs[i-5:i+6]):
                swing_highs.append(highs[i])
            if lows[i] == min(lows[i-5:i+6]):
                swing_lows.append(lows[i])
        
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            hh = swing_highs[-1] > swing_highs[-2]
            hl = swing_lows[-1] > swing_lows[-2]
            lh = swing_highs[-1] < swing_highs[-2]
            ll = swing_lows[-1] < swing_lows[-2]
            
            if hh and hl: return "HH_HL"
            if lh and ll: return "LH_LL"
        return "MIXED"
    
    def _trend_strength(self, df: pd.DataFrame) -> float:
        """Simple trend strength: abs(price change) / total path."""
        closes = df['close'].values
        net_change = abs(closes[-1] - closes[-50])
        total_path = sum(abs(closes[i] - closes[i-1]) for i in range(-49, 0))
        return net_change / total_path if total_path > 0 else 0
    
    def _volatility_state(self, df: pd.DataFrame) -> str:
        atr_recent = (df['high'] - df['low']).iloc[-10:].mean()
        atr_older = (df['high'] - df['low']).iloc[-30:-10].mean()
        if atr_older > 0:
            change = (atr_recent - atr_older) / atr_older
            if change > 0.2: return "EXPANDING"
            if change < -0.2: return "CONTRACTING"
        return "STABLE"


if __name__ == '__main__':
    import MetaTrader5 as mt5
    mt5.initialize()
    detector = StructureDetector()
    
    for pair in ['EURUSD', 'GBPUSD']:
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
        df = pd.DataFrame(rates)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        result = detector.analyze(pair, df)
        print(f"\n{pair}: {result.phase} conf={result.confidence:.0f}%")
        for d in result.details:
            print(f"  {d}")
    
    mt5.shutdown()
