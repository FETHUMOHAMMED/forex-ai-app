"""Canonical Feature Contract - ONE source of truth for ALL feature engineering.
Training = build_features()
Live     = build_features()    <-- SAME FUNCTION
Backtest = build_features()    <-- SAME FUNCTION
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np

FEATURE_COLUMNS = [
    "swing_high_20", "swing_low_20", "liquidity_sweep_high", "liquidity_sweep_low",
    "order_block_high", "order_block_low", "fair_value_gap_high", "fair_value_gap_low",
    "breaker_block_high", "breaker_block_low",
    "ema_20", "ema_50", "ema_200", "atr_14", "rsi_14",
    "macd_line", "macd_signal", "bb_upper", "bb_lower", "adx_14",
    "delta_volume", "cumulative_delta", "vwap_daily", "vwap_weekly", "poc_price",
    "regime_trending_bull", "regime_trending_bear", "regime_ranging", "regime_breakout", "regime_volatile",
    "session_london", "session_ny", "session_asian",
    "range_to_atr", "price_to_vwap", "ema_slope_20", "ema_slope_50", "spread_pct",
]

@dataclass(frozen=True)
class FeatureVector:
    values: Dict[str, float]
    def __post_init__(self):
        missing = set(FEATURE_COLUMNS) - set(self.values.keys())
        if missing: raise ValueError(f"Missing features: {missing}")
        extra = set(self.values.keys()) - set(FEATURE_COLUMNS)
        if extra: raise ValueError(f"Unknown features: {extra}")
    def to_array(self) -> np.ndarray:
        return np.array([self.values[col] for col in FEATURE_COLUMNS], dtype=np.float32)

@dataclass
class MarketData:
    symbol: str; open: float; high: float; low: float; close: float; volume: float
    timestamp_utc: str; timeframe: str = "H1"
    highs_20: Optional[List[float]] = None; lows_20: Optional[List[float]] = None
    closes_50: Optional[List[float]] = None; closes_200: Optional[List[float]] = None
    atr_history: Optional[List[float]] = None; volume_history: Optional[List[float]] = None

def build_features(md: MarketData) -> FeatureVector:
    if md.timeframe != "H1":
        raise ValueError(f"build_features only supports H1, got {md.timeframe}")
    
    f = {}
    # Price Action
    if md.highs_20:
        f["swing_high_20"] = max(md.highs_20)
        f["swing_low_20"] = min(md.lows_20) if md.lows_20 else 0
        f["liquidity_sweep_high"] = 1.0 if md.high > f["swing_high_20"] else 0.0
        f["liquidity_sweep_low"] = 1.0 if md.low < f["swing_low_20"] else 0.0
    else:
        for k in ["swing_high_20","swing_low_20","liquidity_sweep_high","liquidity_sweep_low"]:
            f[k] = 0.0
    
    f["order_block_high"] = f.get("swing_high_20", md.high)
    f["order_block_low"] = f.get("swing_low_20", md.low)
    f["fair_value_gap_high"] = md.high
    f["fair_value_gap_low"] = md.low
    f["breaker_block_high"] = f.get("swing_high_20", md.high)
    f["breaker_block_low"] = f.get("swing_low_20", md.low)
    
    # Technical
    f["ema_20"] = sum(md.closes_50[-20:])/20 if md.closes_50 and len(md.closes_50)>=20 else md.close
    f["ema_50"] = sum(md.closes_50[-50:])/50 if md.closes_50 and len(md.closes_50)>=50 else md.close
    f["ema_200"] = sum(md.closes_200[-200:])/200 if md.closes_200 and len(md.closes_200)>=200 else md.close
    f["atr_14"] = (md.high - md.low) * 1.5
    f["rsi_14"] = 50.0
    f["macd_line"] = 0.0; f["macd_signal"] = 0.0
    f["bb_upper"] = f["ema_20"] * 1.02; f["bb_lower"] = f["ema_20"] * 0.98
    f["adx_14"] = 25.0
    
    # Institutional
    f["delta_volume"] = md.volume if md.close > md.open else -md.volume
    f["cumulative_delta"] = 0.0; f["vwap_daily"] = md.close; f["vwap_weekly"] = md.close
    f["poc_price"] = md.close
    
    # Regime (one-hot)
    r = "volatile" if (md.high-md.low) > f["atr_14"]*1.5 else "ranging"
    for regime in ["trending_bull","trending_bear","ranging","breakout","volatile"]:
        f[f"regime_{regime}"] = 1.0 if r == regime else 0.0
    
    # Session
    hour = int(md.timestamp_utc[11:13]) if len(md.timestamp_utc) > 13 else 12
    f["session_london"] = 1.0 if 7 <= hour < 16 else 0.0
    f["session_ny"] = 1.0 if 12 <= hour < 21 else 0.0
    f["session_asian"] = 1.0 if 0 <= hour < 7 else 0.0
    
    # Derived
    f["range_to_atr"] = (md.high - md.low) / max(f["atr_14"], 0.00001)
    f["price_to_vwap"] = md.close / max(f["vwap_daily"], 0.00001)
    f["ema_slope_20"] = 0.0; f["ema_slope_50"] = 0.0
    f["spread_pct"] = 0.0001
    
    return FeatureVector(values=f)
