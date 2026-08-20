"""STRATEGY V1 - Fully Deterministic, No AI Components."""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone
from enum import Enum

class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"

class MarketRegime(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"

@dataclass
class StrategyV1Config:
    """All parameters explicit and testable."""
    
    # H4 Bias Parameters
    h4_ema_fast: int = 50
    h4_ema_slow: int = 200
    h4_bias_confirmation_bars: int = 3
    
    # Liquidity Sweep Parameters
    sweep_lookback_bars: int = 50
    sweep_wick_ratio_min: float = 0.5
    sweep_body_ratio_max: float = 0.3
    
    # MSS Parameters
    mss_lookback_bars: int = 20
    mss_break_pips_min: float = 2.0
    mss_confirmation_bars: int = 2
    
    # FVG Parameters
    fvg_min_size_pips: float = 3.0
    fvg_max_age_bars: int = 10
    fvg_fill_ratio_max: float = 0.5
    
    # Entry Parameters
    max_spread_pips: float = 1.5
    max_slippage_pips: float = 0.5
    
    # Risk Parameters
    sl_buffer_pips: float = 1.5
    tp_rr_ratio: float = 2.0
    max_risk_per_trade_pct: float = 0.0005
    
    # Session Parameters
    session_start_hour: int = 7
    session_end_hour: int = 11
    trading_days: List[int] = None  # 0=Monday, 4=Friday
    
    def __post_init__(self):
        if self.trading_days is None:
            self.trading_days = [0, 1, 2, 3, 4]

class StrategyV1:
    """Deterministic trading strategy with zero AI components."""
    
    def __init__(self, config: StrategyV1Config = None):
        self.config = config or StrategyV1Config()
        self.version = "V1_DETERMINISTIC"
        
    def analyze(self, h4_data: pd.DataFrame, m15_data: pd.DataFrame, 
                m5_data: pd.DataFrame) -> Dict:
        """
        Complete deterministic analysis pipeline.
        Returns full analysis with entry signal if valid.
        """
        analysis = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": self.version,
            "steps": {},
            "signal": None
        }
        
        # Step 1: H4 Bias
        h4_bias = self._determine_h4_bias(h4_data)
        analysis["steps"]["h4_bias"] = h4_bias
        
        if h4_bias["direction"] == Direction.NONE.value:
            analysis["signal"] = self._no_signal("NO_H4_BIAS")
            return analysis
        
        # Step 2: Liquidity Sweep on M15
        sweep = self._detect_liquidity_sweep(m15_data, h4_bias["direction"])
        analysis["steps"]["liquidity_sweep"] = sweep
        
        if not sweep["detected"]:
            analysis["signal"] = self._no_signal("NO_LIQUIDITY_SWEEP")
            return analysis
        
        # Step 3: MSS on M5
        mss = self._detect_mss(m5_data, h4_bias["direction"])
        analysis["steps"]["mss"] = mss
        
        if not mss["confirmed"]:
            analysis["signal"] = self._no_signal("NO_MSS_CONFIRMATION")
            return analysis
        
        # Step 4: FVG/OB Detection
        fvg = self._detect_fvg(m5_data, h4_bias["direction"])
        analysis["steps"]["fvg"] = fvg
        
        if not fvg["valid"]:
            analysis["signal"] = self._no_signal("NO_VALID_FVG")
            return analysis
        
        # Step 5: Entry Signal Generation
        entry = self._generate_entry_signal(
            h4_bias, sweep, mss, fvg, m5_data
        )
        analysis["steps"]["entry"] = entry
        analysis["signal"] = entry
        
        return analysis
    
    def _determine_h4_bias(self, data: pd.DataFrame) -> Dict:
        """Determine H4 directional bias using EMAs."""
        if len(data) < self.config.h4_ema_slow:
            return {"direction": Direction.NONE.value, "reason": "INSUFFICIENT_DATA"}
        
        # Calculate EMAs
        ema_fast = data['close'].ewm(span=self.config.h4_ema_fast).mean()
        ema_slow = data['close'].ewm(span=self.config.h4_ema_slow).mean()
        
        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]
        current_price = data['close'].iloc[-1]
        
        # Determine trend
        if current_fast > current_slow and current_price > ema_fast.iloc[-1]:
            return {
                "direction": Direction.BUY.value,
                "strength": (current_fast - current_slow) / current_slow,
                "price_above_fast_ema": current_price > ema_fast.iloc[-1],
                "price_above_slow_ema": current_price > ema_slow.iloc[-1]
            }
        elif current_fast < current_slow and current_price < ema_fast.iloc[-1]:
            return {
                "direction": Direction.SELL.value,
                "strength": (current_slow - current_fast) / current_slow,
                "price_below_fast_ema": current_price < ema_fast.iloc[-1],
                "price_below_slow_ema": current_price < ema_slow.iloc[-1]
            }
        else:
            return {"direction": Direction.NONE.value, "reason": "NO_CLEAR_TREND"}
    
    def _detect_liquidity_sweep(self, data: pd.DataFrame, direction: str) -> Dict:
        """Detect liquidity sweep on M15."""
        if len(data) < self.config.sweep_lookback_bars:
            return {"detected": False, "reason": "INSUFFICIENT_DATA"}
        
        lookback = data.iloc[-self.config.sweep_lookback_bars:-1]
        current = data.iloc[-1]
        
        if direction == Direction.BUY.value:
            # Look for sweep of recent lows
            recent_low = lookback['low'].min()
            if current['low'] < recent_low:
                # Price swept below recent low
                candle_range = current['high'] - current['low']
                if candle_range > 0:
                    lower_wick = current['close'] - current['low'] if current['close'] > current['open'] else current['open'] - current['low']
                    wick_ratio = lower_wick / candle_range
                    
                    if wick_ratio >= self.config.sweep_wick_ratio_min:
                        return {
                            "detected": True,
                            "type": "BULLISH_SWEEP",
                            "swept_level": recent_low,
                            "wick_ratio": wick_ratio,
                            "candle_close": current['close'],
                            "candle_open": current['open']
                        }
        
        elif direction == Direction.SELL.value:
            # Look for sweep of recent highs
            recent_high = lookback['high'].max()
            if current['high'] > recent_high:
                candle_range = current['high'] - current['low']
                if candle_range > 0:
                    upper_wick = current['high'] - current['close'] if current['close'] < current['open'] else current['high'] - current['open']
                    wick_ratio = upper_wick / candle_range
                    
                    if wick_ratio >= self.config.sweep_wick_ratio_min:
                        return {
                            "detected": True,
                            "type": "BEARISH_SWEEP",
                            "swept_level": recent_high,
                            "wick_ratio": wick_ratio,
                            "candle_close": current['close'],
                            "candle_open": current['open']
                        }
        
        return {"detected": False, "reason": "NO_SWEEP_DETECTED"}
    
    def _detect_mss(self, data: pd.DataFrame, direction: str) -> Dict:
        """Detect Market Structure Shift on M5."""
        if len(data) < self.config.mss_lookback_bars:
            return {"confirmed": False, "reason": "INSUFFICIENT_DATA"}
        
        lookback = data.iloc[-self.config.mss_lookback_bars:-1]
        current = data.iloc[-1]
        
        if direction == Direction.BUY.value:
            # For bullish MSS: price breaks above recent lower high
            recent_highs = lookback['high'].nlargest(3)
            if len(recent_highs) >= 3:
                resistance = recent_highs.iloc[1]  # Second highest
                break_pips = (current['close'] - resistance) / 0.0001
                
                if break_pips >= self.config.mss_break_pips_min:
                    # Check confirmation
                    if len(data) >= 2:
                        prev_close = data['close'].iloc[-2]
                        if current['close'] > prev_close:
                            return {
                                "confirmed": True,
                                "type": "BULLISH_MSS",
                                "breakout_level": resistance,
                                "break_pips": break_pips,
                                "confirmation": "CLOSE_ABOVE_RESISTANCE"
                            }
        
        elif direction == Direction.SELL.value:
            # For bearish MSS: price breaks below recent higher low
            recent_lows = lookback['low'].nsmallest(3)
            if len(recent_lows) >= 3:
                support = recent_lows.iloc[1]  # Second lowest
                break_pips = (support - current['close']) / 0.0001
                
                if break_pips >= self.config.mss_break_pips_min:
                    if len(data) >= 2:
                        prev_close = data['close'].iloc[-2]
                        if current['close'] < prev_close:
                            return {
                                "confirmed": True,
                                "type": "BEARISH_MSS",
                                "breakout_level": support,
                                "break_pips": break_pips,
                                "confirmation": "CLOSE_BELOW_SUPPORT"
                            }
        
        return {"confirmed": False, "reason": "NO_MSS_CONFIRMED"}
    
    def _detect_fvg(self, data: pd.DataFrame, direction: str) -> Dict:
        """Detect Fair Value Gap on M5."""
        if len(data) < 3:
            return {"valid": False, "reason": "INSUFFICIENT_DATA"}
        
        # Get last 3 candles for FVG detection
        candle_1 = data.iloc[-3]  # Oldest
        candle_2 = data.iloc[-2]
        candle_3 = data.iloc[-1]  # Current
        
        if direction == Direction.BUY.value:
            # Bullish FVG: candle 1 high < candle 3 low
            if candle_1['high'] < candle_3['low']:
                gap_size = (candle_3['low'] - candle_1['high']) / 0.0001
                
                if gap_size >= self.config.fvg_min_size_pips:
                    # Check if FVG is recent (not too old)
                    bars_since_fvg = 1
                    if bars_since_fvg <= self.config.fvg_max_age_bars:
                        return {
                            "valid": True,
                            "type": "BULLISH_FVG",
                            "gap_size_pips": gap_size,
                            "fvg_top": candle_3['low'],
                            "fvg_bottom": candle_1['high'],
                            "age_bars": bars_since_fvg
                        }
        
        elif direction == Direction.SELL.value:
            # Bearish FVG: candle 1 low > candle 3 high
            if candle_1['low'] > candle_3['high']:
                gap_size = (candle_1['low'] - candle_3['high']) / 0.0001
                
                if gap_size >= self.config.fvg_min_size_pips:
                    bars_since_fvg = 1
                    if bars_since_fvg <= self.config.fvg_max_age_bars:
                        return {
                            "valid": True,
                            "type": "BEARISH_FVG",
                            "gap_size_pips": gap_size,
                            "fvg_top": candle_1['low'],
                            "fvg_bottom": candle_3['high'],
                            "age_bars": bars_since_fvg
                        }
        
        return {"valid": False, "reason": "NO_VALID_FVG"}
    
    def _generate_entry_signal(self, h4_bias: Dict, sweep: Dict, 
                               mss: Dict, fvg: Dict, 
                               m5_data: pd.DataFrame) -> Dict:
        """Generate entry signal with precise levels."""
        current_price = m5_data['close'].iloc[-1]
        direction = h4_bias["direction"]
        
        if direction == Direction.BUY.value:
            entry = current_price
            sl = fvg["fvg_bottom"] - (self.config.sl_buffer_pips * 0.0001)
            risk = entry - sl
            tp = entry + (risk * self.config.tp_rr_ratio)
            
            return {
                "direction": Direction.BUY.value,
                "entry": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "risk_pips": risk / 0.0001,
                "reward_pips": (tp - entry) / 0.0001,
                "rr_ratio": self.config.tp_rr_ratio,
                "position_size": self._calculate_position_size(entry, sl),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        elif direction == Direction.SELL.value:
            entry = current_price
            sl = fvg["fvg_top"] + (self.config.sl_buffer_pips * 0.0001)
            risk = sl - entry
            tp = entry - (risk * self.config.tp_rr_ratio)
            
            return {
                "direction": Direction.SELL.value,
                "entry": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "risk_pips": risk / 0.0001,
                "reward_pips": (entry - tp) / 0.0001,
                "rr_ratio": self.config.tp_rr_ratio,
                "position_size": self._calculate_position_size(entry, sl),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _calculate_position_size(self, entry: float, sl: float) -> float:
        """Calculate position size based on risk."""
        risk_amount = self.config.max_risk_per_trade_pct * 100000  # For $100k account
        sl_distance = abs(entry - sl)
        
        if sl_distance == 0:
            return 0.0
        
        # Simplified: 1 pip = $10 per 1.0 lot for EURUSD
        pip_value = 10.0
        sl_pips = sl_distance / 0.0001
        position_size = risk_amount / (sl_pips * pip_value)
        
        return round(position_size, 2)
    
    def _no_signal(self, reason: str) -> Dict:
        """Return no-signal response."""
        return {
            "direction": Direction.NONE.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    # Test with sample data
    import numpy as np
    
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range('2026-08-01', periods=500, freq='5min')
    
    h4_data = pd.DataFrame({
        'open': np.random.randn(500).cumsum() + 100,
        'high': np.random.randn(500).cumsum() + 101,
        'low': np.random.randn(500).cumsum() + 99,
        'close': np.random.randn(500).cumsum() + 100,
    }, index=dates[:500])
    
    m15_data = pd.DataFrame({
        'open': np.random.randn(500).cumsum() + 100,
        'high': np.random.randn(500).cumsum() + 101,
        'low': np.random.randn(500).cumsum() + 99,
        'close': np.random.randn(500).cumsum() + 100,
    }, index=dates[:500])
    
    m5_data = pd.DataFrame({
        'open': np.random.randn(500).cumsum() + 100,
        'high': np.random.randn(500).cumsum() + 101,
        'low': np.random.randn(500).cumsum() + 99,
        'close': np.random.randn(500).cumsum() + 100,
    }, index=dates[:500])
    
    strategy = StrategyV1()
    result = strategy.analyze(h4_data, m15_data, m5_data)
    
    print("Strategy V1 Analysis Result:")
    print(json.dumps(result, indent=2, default=str))
