"""
Volume 8: Institutional Market Regime Intelligence
Answers: "What type of market are we in, and is this trade suitable?"

Regimes:
  TRENDING_BULL, TRENDING_BEAR - Strong directional moves
  RANGING - Sideways, mean-reverting
  BREAKOUT - Volatility expansion, new levels
  VOLATILE - High ATR, unpredictable
  LOW_VOLATILITY - Compression, waiting for expansion
  ACCUMULATION - Volume building, range-bound buying
  DISTRIBUTION - Volume building, range-bound selling

Design rule: This module does NOT generate BUY/SELL signals.
It only approves or rejects trades based on regime suitability.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict


@dataclass
class RegimeResult:
    """Complete regime assessment"""
    pair: str
    timestamp: str

    # Primary regime
    regime: str = "UNKNOWN"  # TRENDING_BULL, TRENDING_BEAR, RANGING, BREAKOUT, VOLATILE, LOW_VOLATILITY, ACCUMULATION, DISTRIBUTION
    regime_confidence: float = 0.0  # 0-100%

    # Component states
    atr_state: str = "NORMAL"  # HIGH, NORMAL, LOW
    volatility_state: str = "STABLE"  # EXPANDING, STABLE, CONTRACTING
    trend_strength: str = "NEUTRAL"  # STRONG, HEALTHY, WEAK, NEUTRAL
    volume_state: str = "NORMAL"  # HIGH, NORMAL, LOW
    structure_state: str = "RANGE"  # TRENDING, RANGE, BREAKOUT

    # Scores
    trend_score: float = 0.0
    volatility_score: float = 0.0
    volume_score: float = 0.0
    structure_score: float = 0.0
    composite_score: float = 0.0

    # Trade suitability
    buy_suitable: bool = False
    sell_suitable: bool = False
    suitability_reason: str = ""

    # Historical context
    previous_regime: str = "UNKNOWN"
    regime_change: bool = False


class MarketRegimeEngine:
    """
    Detects the current market regime and evaluates trade suitability.

    Uses data from Volumes 1-3 to classify the environment.
    Does NOT generate trading signals - only approves/rejects based on regime.
    """

    def __init__(self):
        # Lookback periods
        self.trend_lookback = 50
        self.volatility_lookback = 20
        self.atr_period = 14

        # Thresholds
        self.trend_strength_threshold = 0.003  # 0.3% price change over lookback
        self.strong_trend_threshold = 0.006    # 0.6% = strong trend
        self.volatility_expansion_threshold = 0.2  # 20% ATR increase
        self.volatility_contraction_threshold = -0.2  # 20% ATR decrease

        # Regime history for change detection
        self.regime_history: Dict[str, str] = {}

        # Trade suitability rules
        self.regime_rules = {
            'TRENDING_BULL': {'buy': True, 'sell': False, 'reason': 'Trending up - buys only'},
            'TRENDING_BEAR': {'buy': False, 'sell': True, 'reason': 'Trending down - sells only'},
            'RANGING': {'buy': True, 'sell': True, 'reason': 'Range-bound - both directions OK with caution'},
            'BREAKOUT': {'buy': True, 'sell': True, 'reason': 'Breakout - trade in breakout direction'},
            'VOLATILE': {'buy': False, 'sell': False, 'reason': 'Too volatile - stand aside'},
            'LOW_VOLATILITY': {'buy': False, 'sell': False, 'reason': 'Compression - wait for expansion'},
            'ACCUMULATION': {'buy': True, 'sell': False, 'reason': 'Accumulation - buys preferred'},
            'DISTRIBUTION': {'buy': False, 'sell': True, 'reason': 'Distribution - sells preferred'},
        }

    def analyze(self, pair: str, df: pd.DataFrame,
                microstructure_result=None,
                liquidity_result=None,
                structure_result=None) -> RegimeResult:
        """
        Analyze current market regime.

        Args:
            pair: Trading pair
            df: OHLCV DataFrame
            microstructure_result: From Volume 1
            liquidity_result: From Volume 2
            structure_result: From Volume 3

        Returns:
            RegimeResult with full regime assessment
        """
        result = RegimeResult(
            pair=pair,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        if len(df) < self.trend_lookback:
            result.regime = "UNKNOWN"
            result.suitability_reason = "Insufficient data"
            return result

        # 1. Trend Detection
        trend_score, trend_strength, trend_direction = self._detect_trend(df)
        result.trend_score = trend_score
        result.trend_strength = trend_strength

        # 2. Volatility Detection
        vol_score, vol_state, atr_state = self._detect_volatility(df)
        result.volatility_score = vol_score
        result.volatility_state = vol_state
        result.atr_state = atr_state

        # 3. Volume Analysis
        vol_score_v, volume_state = self._analyze_volume(df)
        result.volume_score = vol_score_v
        result.volume_state = volume_state

        # 4. Structure Assessment (from Volume 3 if available)
        struct_score = 50.0
        structure_state = "RANGE"
        if structure_result is not None:
            bias = getattr(structure_result, 'structure_bias', 'RANGE')
            if 'TRENDING' in str(bias).upper():
                structure_state = "TRENDING"
                struct_score = 70
            elif 'BREAKOUT' in str(bias).upper():
                structure_state = "BREAKOUT"
                struct_score = 65
            elif 'RANGE' in str(bias).upper():
                structure_state = "RANGE"
                struct_score = 40
        result.structure_score = struct_score
        result.structure_state = structure_state

        # 5. Determine Primary Regime
        result.composite_score = (
            trend_score * 0.30 +
            vol_score * 0.25 +
            vol_score_v * 0.20 +
            struct_score * 0.25
        )

        result.regime = self._classify_regime(
            trend_direction, trend_strength, vol_state, volume_state, structure_state
        )
        result.regime_confidence = result.composite_score

        # 6. Check regime change
        prev = self.regime_history.get(pair, "UNKNOWN")
        result.previous_regime = prev
        result.regime_change = (prev != result.regime)
        self.regime_history[pair] = result.regime

        # 7. Trade Suitability
        rules = self.regime_rules.get(result.regime, {'buy': False, 'sell': False, 'reason': 'Unknown regime'})
        result.buy_suitable = rules['buy']
        result.sell_suitable = rules['sell']
        result.suitability_reason = rules['reason']

        return result

    def is_trade_suitable(self, regime_result: RegimeResult, signal_direction: str) -> tuple:
        """
        Check if a specific trade direction is suitable for the current regime.

        Args:
            regime_result: From analyze()
            signal_direction: 'BUY' or 'SELL'

        Returns:
            (suitable: bool, reason: str)
        """
        if signal_direction == 'BUY':
            return regime_result.buy_suitable, regime_result.suitability_reason
        elif signal_direction == 'SELL':
            return regime_result.sell_suitable, regime_result.suitability_reason
        return False, "Invalid direction"

    def _detect_trend(self, df: pd.DataFrame) -> tuple:
        """Detect trend strength and direction. Returns (score, strength, direction)."""
        closes = df['close'].values

        # Price change over lookback
        price_change = (closes[-1] - closes[-self.trend_lookback]) / closes[-self.trend_lookback]

        # Linear regression slope
        x = np.arange(len(closes[-self.trend_lookback:]))
        y = closes[-self.trend_lookback:]
        slope = np.polyfit(x, y, 1)[0]
        slope_normalized = slope / np.mean(y)

        # Determine direction
        if price_change > self.trend_strength_threshold:
            direction = "BULLISH"
        elif price_change < -self.trend_strength_threshold:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # Determine strength
        abs_change = abs(price_change)
        if abs_change > self.strong_trend_threshold:
            strength = "STRONG"
            score = 85
        elif abs_change > self.trend_strength_threshold:
            strength = "HEALTHY"
            score = 65
        elif abs_change > self.trend_strength_threshold * 0.5:
            strength = "WEAK"
            score = 45
        else:
            strength = "NEUTRAL"
            score = 30

        return score, strength, direction

    def _detect_volatility(self, df: pd.DataFrame) -> tuple:
        """Detect volatility regime. Returns (score, vol_state, atr_state)."""
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        # ATR calculation
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                abs(high[1:] - close[:-1]),
                abs(low[1:] - close[:-1])
            )
        )
        atr_current = np.mean(tr[-self.atr_period:]) if len(tr) >= self.atr_period else 0
        atr_previous = np.mean(tr[-(self.atr_period*2):-self.atr_period]) if len(tr) >= self.atr_period*2 else atr_current

        if atr_previous > 0:
            atr_change = (atr_current - atr_previous) / atr_previous
        else:
            atr_change = 0.0

        # ATR state
        atr_pct = atr_current / np.mean(close[-self.atr_period:]) if np.mean(close[-self.atr_period:]) > 0 else 0

        if atr_pct > 0.008:
            atr_state = "HIGH"
        elif atr_pct < 0.003:
            atr_state = "LOW"
        else:
            atr_state = "NORMAL"

        # Volatility state
        if atr_change > self.volatility_expansion_threshold:
            vol_state = "EXPANDING"
            score = 70
        elif atr_change < self.volatility_contraction_threshold:
            vol_state = "CONTRACTING"
            score = 35
        else:
            vol_state = "STABLE"
            score = 50

        return score, vol_state, atr_state

    def _analyze_volume(self, df: pd.DataFrame) -> tuple:
        """Analyze volume characteristics. Returns (score, volume_state)."""
        if 'volume' not in df.columns:
            return 50.0, "NORMAL"

        recent_vol = df['volume'].iloc[-20:].mean()
        older_vol = df['volume'].iloc[-40:-20].mean()

        if older_vol > 0:
            vol_change = (recent_vol - older_vol) / older_vol
        else:
            vol_change = 0.0

        if vol_change > 0.3:
            volume_state = "HIGH"
            score = 70
        elif vol_change < -0.3:
            volume_state = "LOW"
            score = 30
        else:
            volume_state = "NORMAL"
            score = 50

        return score, volume_state

    def _classify_regime(self, trend_direction: str, trend_strength: str,
                         vol_state: str, volume_state: str,
                         structure_state: str) -> str:
        """Classify the primary market regime."""

        # Trending markets
        if trend_direction in ("BULLISH", "BEARISH") and trend_strength in ("STRONG", "HEALTHY"):
            if structure_state == "TRENDING":
                return f"TRENDING_{trend_direction}"

        # Breakout
        if vol_state == "EXPANDING" and structure_state == "BREAKOUT":
            return "BREAKOUT"

        # Volatile
        if vol_state == "EXPANDING" and trend_strength == "NEUTRAL":
            return "VOLATILE"

        # Low volatility / compression
        if vol_state == "CONTRACTING" and volume_state == "LOW":
            return "LOW_VOLATILITY"

        # Accumulation / Distribution (range + volume bias)
        if structure_state == "RANGE":
            if volume_state == "HIGH" and trend_direction == "BULLISH":
                return "ACCUMULATION"
            elif volume_state == "HIGH" and trend_direction == "BEARISH":
                return "DISTRIBUTION"
            return "RANGING"

        # Default
        if trend_direction != "NEUTRAL":
            return f"TRENDING_{trend_direction}"
        return "RANGING"


# Quick self-test
if __name__ == "__main__":
    import MetaTrader5 as mt5
    mt5.initialize()
    mt5.symbol_select('USDJPYm', True)
    rates = mt5.copy_rates_from_pos('USDJPYm', mt5.TIMEFRAME_M15, 0, 200)
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    engine = MarketRegimeEngine()
    result = engine.analyze('USDJPY', df)
    print(f"Regime: {result.regime} (confidence: {result.regime_confidence:.0f}%)")
    print(f"Trend: {result.trend_strength} | Vol: {result.volatility_state} | ATR: {result.atr_state}")
    print(f"Buy suitable: {result.buy_suitable} | Sell suitable: {result.sell_suitable}")
    print(f"Reason: {result.suitability_reason}")
    print(f"Regime change: {result.regime_change} (was: {result.previous_regime})")
    mt5.shutdown()
