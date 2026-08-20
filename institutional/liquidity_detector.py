"""
Liquidity Detector V2 - Independent, explainable, validated.
Replaces the monolithic score with meaningful components.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class LiquidityResult:
    state: str  # SWEEP_BULLISH, SWEEP_BEARISH, IMBALANCE, NO_EVENT
    confidence: float  # 0-100
    sweep_detected: bool
    sweep_direction: str
    sweep_strength: float  # 0-1
    imbalance_ratio: float  # bull/bear volume ratio
    details: list  # Human-readable reasons

class LiquidityDetector:
    """Detects liquidity events with confidence scores."""
    
    def analyze(self, pair: str, df: pd.DataFrame) -> LiquidityResult:
        details = []
        confidence = 50.0
        
        # 1. Sweep detection (20 candles)
        sweep = self._detect_sweep(df)
        if sweep['detected']:
            details.append(f"Sweep {sweep['direction']} at {sweep['level']:.5f}")
            confidence += 25
        else:
            details.append("No sweep detected")
        
        # 2. Volume imbalance
        imbalance = self._volume_imbalance(df)
        if imbalance > 0.3:
            details.append(f"Strong volume imbalance ({imbalance:.2f})")
            confidence += 15
        elif imbalance > 0.15:
            details.append(f"Moderate volume imbalance ({imbalance:.2f})")
            confidence += 8
        
        # 3. Price rejection (wicks)
        rejection = self._price_rejection(df)
        if rejection['detected']:
            details.append(f"Price rejection: {rejection['direction']}")
            confidence += 10
        
        confidence = min(100, max(0, confidence))
        
        # Determine state
        if sweep['detected']:
            state = f"SWEEP_{sweep['direction'].upper()}"
        elif imbalance > 0.2:
            state = "IMBALANCE"
        else:
            state = "LOW_LIQUIDITY"
        
        return LiquidityResult(
            state=state,
            confidence=confidence,
            sweep_detected=sweep['detected'],
            sweep_direction=sweep.get('direction', 'none'),
            sweep_strength=sweep.get('strength', 0),
            imbalance_ratio=imbalance,
            details=details
        )
    
    def _detect_sweep(self, df: pd.DataFrame) -> dict:
        """Detect liquidity sweeps with strength scoring."""
        recent = df.iloc[-20:]
        highs = df['high'].values
        lows = df['low'].values
        
        # Find swing highs/lows
        swing_highs = []
        swing_lows = []
        for i in range(10, len(df)-10):
            if highs[i] == max(highs[i-10:i+11]):
                swing_highs.append({'index': i, 'price': highs[i]})
            if lows[i] == min(lows[i-10:i+11]):
                swing_lows.append({'index': i, 'price': lows[i]})
        
        # Check recent sweeps
        for sh in swing_highs[-3:]:
            level = sh['price']
            broke_above = any(recent['high'] > level * 1.0002)
            closed_below = recent['close'].iloc[-1] < level
            if broke_above and closed_below:
                strength = min(1.0, (max(recent['high']) - level) / (level * 0.001))
                return {'detected': True, 'direction': 'sell', 'level': level, 'strength': strength}
        
        for sl in swing_lows[-3:]:
            level = sl['price']
            broke_below = any(recent['low'] < level * 0.9998)
            closed_above = recent['close'].iloc[-1] > level
            if broke_below and closed_above:
                strength = min(1.0, (level - min(recent['low'])) / (level * 0.001))
                return {'detected': True, 'direction': 'buy', 'level': level, 'strength': strength}
        
        return {'detected': False, 'direction': None, 'level': None, 'strength': 0}
    
    def _volume_imbalance(self, df: pd.DataFrame) -> float:
        """Calculate bull vs bear volume ratio."""
        if 'volume' not in df.columns:
            return 0.0
        recent = df.iloc[-20:]
        bull_vol = float(recent[recent['close'] > recent['open']]['volume'].sum())
        bear_vol = float(recent[recent['close'] < recent['open']]['volume'].sum())
        total = bull_vol + bear_vol
        return abs(bull_vol - bear_vol) / total if total > 0 else 0.0
    
    def _price_rejection(self, df: pd.DataFrame) -> dict:
        """Detect price rejection via wicks."""
        recent = df.iloc[-5:]
        for i in range(len(recent)):
            candle = recent.iloc[i]
            body = abs(float(candle['close']) - float(candle['open']))
            upper_wick = float(candle['high']) - max(float(candle['close']), float(candle['open']))
            lower_wick = min(float(candle['close']), float(candle['open'])) - float(candle['low'])
            
            if upper_wick > body * 2:
                return {'detected': True, 'direction': 'sell'}
            if lower_wick > body * 2:
                return {'detected': True, 'direction': 'buy'}
        return {'detected': False, 'direction': None}


if __name__ == '__main__':
    import MetaTrader5 as mt5
    mt5.initialize()
    detector = LiquidityDetector()
    
    for pair in ['EURUSD', 'GBPUSD']:
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
        df = pd.DataFrame(rates)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        result = detector.analyze(pair, df)
        print(f"\n{pair}: {result.state} conf={result.confidence:.0f}%")
        for d in result.details:
            print(f"  {d}")
    
    mt5.shutdown()
