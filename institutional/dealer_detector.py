"""
Dealer Pressure Detector V2 - Independent, explainable.
Detects buying/selling pressure from volume and price action.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class DealerResult:
    pressure: str  # BUYING_PRESSURE, SELLING_PRESSURE, ACCUMULATING, DISTRIBUTING, NEUTRAL
    confidence: float  # 0-100
    volume_delta: float  # -1 to +1
    price_confirmation: bool
    details: list

class DealerDetector:
    """Detects dealer pressure with confidence scores."""
    
    def analyze(self, pair: str, df: pd.DataFrame) -> DealerResult:
        details = []
        confidence = 50.0
        
        # 1. Volume delta (30 bars)
        delta = self._volume_delta(df, 30)
        abs_delta = abs(delta)
        
        if abs_delta > 0.25:
            details.append(f"Strong volume delta: {delta:+.3f}")
            confidence += 25
        elif abs_delta > 0.10:
            details.append(f"Moderate volume delta: {delta:+.3f}")
            confidence += 12
        else:
            details.append(f"Weak volume delta: {delta:+.3f}")
        
        # 2. Price-volume alignment
        price_change = self._price_change(df, 30)
        aligned = (delta > 0 and price_change > 0) or (delta < 0 and price_change < 0)
        if aligned:
            details.append("Volume aligned with price direction")
            confidence += 10
        
        # 3. Consecutive direction
        consecutive = self._consecutive_direction(df, 10)
        if consecutive:
            details.append(f"Consecutive {consecutive} pressure")
            confidence += 10
        
        # 4. Absorption detection
        absorption = self._detect_absorption(df)
        if absorption:
            details.append(f"Absorption: {absorption}")
            confidence += 5
        
        confidence = min(100, max(0, confidence))
        
        # Classify pressure
        if delta > 0.15 and aligned:
            pressure = "BUYING_PRESSURE"
        elif delta < -0.15 and aligned:
            pressure = "SELLING_PRESSURE"
        elif delta > 0.05:
            pressure = "ACCUMULATING"
        elif delta < -0.05:
            pressure = "DISTRIBUTING"
        else:
            pressure = "NEUTRAL"
        
        return DealerResult(
            pressure=pressure,
            confidence=confidence,
            volume_delta=delta,
            price_confirmation=aligned,
            details=details
        )
    
    def _volume_delta(self, df: pd.DataFrame, period: int) -> float:
        if 'volume' not in df.columns:
            return 0.0
        recent = df.iloc[-period:]
        bull = float(recent[recent['close'] > recent['open']]['volume'].sum())
        bear = float(recent[recent['close'] < recent['open']]['volume'].sum())
        total = bull + bear
        return (bull - bear) / total if total > 0 else 0.0
    
    def _price_change(self, df: pd.DataFrame, period: int) -> float:
        return (float(df['close'].iloc[-1]) - float(df['close'].iloc[-period])) / float(df['close'].iloc[-period])
    
    def _consecutive_direction(self, df: pd.DataFrame, period: int) -> str:
        recent = df.iloc[-period:]
        up = sum(recent['close'] > recent['open'])
        down = sum(recent['close'] < recent['open'])
        if up >= period * 0.7:
            return "bullish"
        elif down >= period * 0.7:
            return "bearish"
        return ""
    
    def _detect_absorption(self, df: pd.DataFrame) -> str:
        """Detect volume absorption: high volume, small price movement."""
        recent = df.iloc[-5:]
        avg_vol = float(recent['volume'].mean()) if 'volume' in df.columns else 0
        prev_vol = float(df['volume'].iloc[-10:-5].mean()) if 'volume' in df.columns else 0
        price_range = (float(recent['high'].max()) - float(recent['low'].min())) / float(recent['close'].iloc[-1])
        
        if prev_vol > 0 and avg_vol > prev_vol * 1.5 and price_range < 0.003:
            return "High volume, tight range - absorption"
        return ""


if __name__ == '__main__':
    import MetaTrader5 as mt5
    mt5.initialize()
    detector = DealerDetector()
    
    for pair in ['EURUSD', 'GBPUSD', 'USDJPY']:
        symbol = pair + 'm'
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
        df = pd.DataFrame(rates)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        result = detector.analyze(pair, df)
        print(f"\n{pair}: {result.pressure} conf={result.confidence:.0f}% delta={result.volume_delta:+.3f}")
        for d in result.details:
            print(f"  {d}")
    
    mt5.shutdown()
