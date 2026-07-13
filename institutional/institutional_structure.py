import pandas as pd
import numpy as np

class InstitutionalStructure:
    """
    Real market structure: Phase detection, trend analysis, structure bias.
    Replaces stub.
    """
    
    def __init__(self):
        self.structure_lookback = 50
        self.atr_period = 14
    
    def analyze(self, pair: str, df: pd.DataFrame):
        if len(df) < self.structure_lookback:
            return self._neutral_result()
        
        recent = df.iloc[-self.structure_lookback:]
        current = df.iloc[-1]
        
        # ATR for volatility
        atr = self._calc_atr(df, self.atr_period)
        atr_pct = atr / current['close'] if current['close'] > 0 else 0
        
        # Market structure: HH/HL or LH/LL
        structure = self._detect_structure(recent)
        
        # Volatility regime
        atr_start = self._calc_atr(df.iloc[:-20], self.atr_period) if len(df) > 20 else atr
        if atr_start > 0:
            atr_change = (atr - atr_start) / atr_start
        else:
            atr_change = 0
        
        if atr_change > 0.2:
            phase = "EXPANDING"
        elif atr_change < -0.2:
            phase = "CONTRACTING"
        else:
            phase = "STABLE"
        
        # Combine structure + phase for bias
        if structure == "HH_HL" and phase != "CONTRACTING":
            bias = "BULLISH_TRENDING"
            continuation_prob = 0.60
        elif structure == "LH_LL" and phase != "CONTRACTING":
            bias = "BEARISH_TRENDING"
            continuation_prob = 0.60
        elif structure == "HH_HL":
            bias = "BULLISH_WEAK"
            continuation_prob = 0.52
        elif structure == "LH_LL":
            bias = "BEARISH_WEAK"
            continuation_prob = 0.52
        elif phase == "CONTRACTING":
            bias = "RANGE_COMPRESSION"
            continuation_prob = 0.48
        elif phase == "EXPANDING":
            bias = "BREAKOUT"
            continuation_prob = 0.55
        else:
            bias = "RANGE"
            continuation_prob = 0.50
        
        # Score
        score = 50
        if "TRENDING" in bias:
            score += 25
        elif "WEAK" in bias:
            score += 10
        if phase == "EXPANDING":
            score += 15
        elif phase == "CONTRACTING":
            score -= 15
        score = min(100, max(0, score))
        
        return StructureResult(
            structure_bias=bias,
            market_phase=phase,
            atr_pct=atr_pct,
            continuation_prob=continuation_prob,
            structure_score=score
        )
    
    def _calc_atr(self, df, period):
        if len(df) < period + 1:
            return 0
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.iloc[-period:].mean()
    
    def _detect_structure(self, df):
        """Detect HH/HL (uptrend) or LH/LL (downtrend)."""
        highs = df['high'].values
        lows = df['low'].values
        
        # Find local highs and lows
        swing_highs = []
        swing_lows = []
        
        for i in range(5, len(df) - 5):
            if highs[i] == max(highs[i-5:i+6]):
                swing_highs.append(highs[i])
            if lows[i] == min(lows[i-5:i+6]):
                swing_lows.append(lows[i])
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "INDETERMINATE"
        
        # Last two swing highs and lows
        hh = swing_highs[-1] > swing_highs[-2]  # Higher high
        hl = swing_lows[-1] > swing_lows[-2]    # Higher low
        lh = swing_highs[-1] < swing_highs[-2]  # Lower high
        ll = swing_lows[-1] < swing_lows[-2]    # Lower low
        
        if hh and hl:
            return "HH_HL"
        elif lh and ll:
            return "LH_LL"
        else:
            return "INDETERMINATE"
    
    def _neutral_result(self):
        return StructureResult(
            structure_bias="RANGE",
            market_phase="STABLE",
            atr_pct=0,
            continuation_prob=0.50,
            structure_score=20
        )


class StructureResult:
    def __init__(self, structure_bias, market_phase, atr_pct, continuation_prob, structure_score):
        self.structure_bias = structure_bias
        self.market_phase = market_phase
        self.atr_pct = atr_pct
        self.continuation_prob = continuation_prob
        self.structure_score = structure_score
        # Compatibility aliases for old code
        self.continuation_probability = continuation_prob
        self.trend_quality = "UNKNOWN"
        self.expansion_state = "UNKNOWN"
        self.institutional_cycle = "UNKNOWN"
