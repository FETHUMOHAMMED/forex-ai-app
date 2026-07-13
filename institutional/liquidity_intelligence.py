import pandas as pd
import numpy as np

class LiquidityIntelligence:
    """
    Real microstructure: Sweep detection, liquidity levels, and order flow analysis.
    Replaces stub that returned NO_LIQUIDITY_EVENT for everything.
    """
    
    def __init__(self):
        self.swing_lookback = 20
        self.sweep_threshold_pips = 2  # Must exceed level by this many pips
        self.sweep_reversal_bars = 3   # Must close back inside within this many bars
    
    def analyze(self, pair: str, df: pd.DataFrame):
        """
        Analyze liquidity conditions from OHLC data.
        Returns object with: liquidity_state, sweep_detected, sweep_level, sweep_direction
        """
        if len(df) < self.swing_lookback + 10:
            return self._neutral_result()
        
        # Find swing highs and lows
        swings = self._find_swings(df)
        
        # Detect sweeps
        sweep = self._detect_sweep(df, swings)
        
        if sweep['detected']:
            return LiquidityResult(
                liquidity_state=f"LIQUIDITY_SWEEP_{'BULLISH' if sweep['direction'] == 'buy' else 'BEARISH'}",
                sweep_detected=True,
                sweep_level=sweep['level'],
                sweep_direction=sweep['direction'],
                sweep_strength=sweep['strength'],
                nearest_liquidity=sweep['level'],
                liquidity_score=sweep['strength'] * 100
            )
        
        # Check proximity to nearest liquidity
        nearest = self._nearest_liquidity(df, swings)
        
        if nearest['proximity_pct'] < 0.15:  # Within 15% of a swing level
            return LiquidityResult(
                liquidity_state="NEAR_LIQUIDITY",
                sweep_detected=False,
                sweep_level=None,
                sweep_direction=None,
                sweep_strength=0,
                nearest_liquidity=nearest['level'],
                liquidity_score=30 + (1 - nearest['proximity_pct']) * 40
            )
        
        return LiquidityResult(
            liquidity_state="NO_LIQUIDITY_EVENT",
            sweep_detected=False,
            sweep_level=None,
            sweep_direction=None,
            sweep_strength=0,
            nearest_liquidity=nearest['level'],
            liquidity_score=10
        )
    
    def _find_swings(self, df):
        """Find swing highs and lows using simple pivot detection."""
        highs = df['high'].values
        lows = df['low'].values
        n = self.swing_lookback
        
        swing_highs = []
        swing_lows = []
        
        for i in range(n, len(df) - n):
            # Swing high: higher than n bars left and right
            if highs[i] == max(highs[i-n:i+n+1]):
                swing_highs.append({'index': i, 'price': highs[i]})
            # Swing low: lower than n bars left and right
            if lows[i] == min(lows[i-n:i+n+1]):
                swing_lows.append({'index': i, 'price': lows[i]})
        
        return {'highs': swing_highs, 'lows': swing_lows}
    
    def _detect_sweep(self, df, swings):
        """Detect if recent price action swept a swing level."""
        recent_bars = df.iloc[-20:]  # Last 20 bars
        current_price = df['close'].iloc[-1]
        
        # Check for sweep of swing highs (bearish sweep)
        for sh in swings['highs'][-5:]:  # Only recent swings
            level = sh['price']
            # Did price break above the level then close back below?
            for i in range(len(recent_bars) - self.sweep_reversal_bars):
                window = recent_bars.iloc[i:i + self.sweep_reversal_bars + 1]
                broke_above = any(window['high'] > level + self._pip_size(df))
                closed_back = window['close'].iloc[-1] < level
                
                if broke_above and closed_back:
                    strength = min(1.0, (max(window['high']) - level) / (level * 0.002))
                    return {
                        'detected': True,
                        'direction': 'sell',
                        'level': level,
                        'strength': strength
                    }
        
        # Check for sweep of swing lows (bullish sweep)
        for sl in swings['lows'][-5:]:
            level = sl['price']
            for i in range(len(recent_bars) - self.sweep_reversal_bars):
                window = recent_bars.iloc[i:i + self.sweep_reversal_bars + 1]
                broke_below = any(window['low'] < level - self._pip_size(df))
                closed_back = window['close'].iloc[-1] > level
                
                if broke_below and closed_back:
                    strength = min(1.0, (level - min(window['low'])) / (level * 0.002))
                    return {
                        'detected': True,
                        'direction': 'buy',
                        'level': level,
                        'strength': strength
                    }
        
        return {'detected': False, 'direction': None, 'level': None, 'strength': 0}
    
    def _nearest_liquidity(self, df, swings):
        """Find distance to nearest swing level as percentage of price."""
        current = df['close'].iloc[-1]
        all_levels = [s['price'] for s in swings['highs'][-5:]] + [s['price'] for s in swings['lows'][-5:]]
        
        if not all_levels:
            return {'level': None, 'proximity_pct': 1.0}
        
        distances = [abs(current - lvl) / current for lvl in all_levels]
        min_dist = min(distances)
        nearest_level = all_levels[distances.index(min_dist)]
        
        return {'level': nearest_level, 'proximity_pct': min_dist}
    
    def _pip_size(self, df):
        """Estimate pip size for the pair."""
        price = df['close'].iloc[-1]
        if price > 100:  # JPY pairs
            return 0.01
        return 0.0001
    
    def _neutral_result(self):
        return LiquidityResult(
            liquidity_state="NO_LIQUIDITY_EVENT",
            sweep_detected=False,
            sweep_level=None,
            sweep_direction=None,
            sweep_strength=0,
            nearest_liquidity=None,
            liquidity_score=10
        )


class LiquidityResult:
    def __init__(self, liquidity_state, sweep_detected, sweep_level, 
                 sweep_direction, sweep_strength, nearest_liquidity, liquidity_score):
        self.liquidity_state = liquidity_state
        self.sweep_detected = sweep_detected
        self.sweep_level = sweep_level
        self.sweep_direction = sweep_direction
        self.sweep_strength = sweep_strength
        self.nearest_liquidity = nearest_liquidity
        self.liquidity_score = liquidity_score
        # Compatibility aliases for old code
        self.nearest_pool = nearest_liquidity
        self.pool_distance_pips = 0
        self.sweep_probability = sweep_strength * 100 if sweep_strength else 0
        self.institutional_interest = sweep_direction or "NONE"
