"""CANONICAL V4 STRATEGY - The ONE true implementation."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional

class CanonicalV4Strategy:
    """
    THE SINGLE SOURCE OF TRUTH for V4 strategy.
    Every test MUST use this exact implementation.
    """
    
    # Strategy parameters (FROZEN - do not modify without revalidation)
    PARAMS = {
        "pair": "USDJPYm",
        "timeframe": mt5.TIMEFRAME_H4,
        "direction": "BUY",
        "ema_fast": 50,
        "ema_slow": 200,
        "atr_period": 14,
        "sl_atr_mult": 2.0,
        "rr_ratio": 2.0,
        "max_hold_bars": 50,
        "sessions": [(7, 11)],  # London session: 07:00-11:00 UTC
        "risk_percent": 0.25,  # EXPLICIT: 0.25%, NOT 25%
        "risk_fraction": 0.0025  # Explicit fraction
    }
    
    def __init__(self):
        self.strategy_version = "V4_CANONICAL_1.0"
        self.params = self.PARAMS.copy()
    
    def load_data(self, bars: int = 10000) -> Optional[pd.DataFrame]:
        """Load market data - THE ONLY way to load data."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(
            self.params["pair"],
            self.params["timeframe"],
            0,
            bars
        )
        mt5.shutdown()
        
        if rates is None:
            return None
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        return data
    
    def generate_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate features - THE ONLY feature generation."""
        df = data.copy()
        
        # EMAs
        df['ema_fast'] = df['close'].ewm(span=self.params["ema_fast"]).mean()
        df['ema_slow'] = df['close'].ewm(span=self.params["ema_slow"]).mean()
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(self.params["atr_period"]).mean()
        
        # FVG
        df['bullish_fvg'] = (df['high'].shift(2) < df['low'])
        
        # Session
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        # Signal
        df['bullish_bias'] = df['ema_fast'] > df['ema_slow']
        df['in_session'] = df['hour'].apply(self._is_in_session)
        
        # Final signal
        df['signal'] = (
            df['bullish_fvg'] & 
            df['bullish_bias'] & 
            df['in_session']
        )
        
        return df
    
    def _is_in_session(self, hour: int) -> bool:
        """Check if hour is in allowed sessions."""
        return any(start <= hour < end for start, end in self.params["sessions"])
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals - THE ONLY signal generation."""
        df = self.generate_features(data)
        return df[df['signal'] == True]
    
    def simulate_trade(self, data: pd.DataFrame, signal_idx: int) -> Dict:
        """Simulate a trade - THE ONLY trade simulation."""
        entry = data['close'].iloc[signal_idx]
        atr = data['atr'].iloc[signal_idx]
        
        # BUY only
        sl = entry - (atr * self.params["sl_atr_mult"])
        tp = entry + (atr * self.params["sl_atr_mult"] * self.params["rr_ratio"])
        
        exit_idx = min(signal_idx + self.params["max_hold_bars"], len(data) - 1)
        
        for j in range(signal_idx + 1, exit_idx):
            if data['low'].iloc[j] <= sl:
                return {"r": -1, "result": "SL", "bars_held": j - signal_idx}
            elif data['high'].iloc[j] >= tp:
                return {"r": self.params["rr_ratio"], "result": "TP", "bars_held": j - signal_idx}
        
        # Timeout
        exit_price = data['close'].iloc[exit_idx]
        r = (exit_price - entry) / (entry - sl)
        return {"r": r, "result": "TIMEOUT", "bars_held": self.params["max_hold_bars"]}
    
    def run_backtest(self, data: pd.DataFrame) -> List[Dict]:
        """Run backtest - THE ONLY backtest implementation."""
        data = self.generate_features(data)
        trades = []
        
        for i in range(200, len(data)):
            if data['signal'].iloc[i]:
                trade = self.simulate_trade(data, i)
                trade.update({
                    "date": data['timestamp'].iloc[i],
                    "hour": data['hour'].iloc[i],
                    "year": data['timestamp'].iloc[i].year
                })
                trades.append(trade)
        
        return trades
    
    def check_current_signal(self) -> Dict:
        """Check for current signal - THE ONLY live signal check."""
        data = self.load_data(bars=200)
        if data is None:
            return {"signal": False, "reason": "NO_DATA"}
        
        data = self.generate_features(data)
        
        # Check last bar
        last = data.iloc[-1]
        
        if not last['signal']:
            if not last['bullish_fvg']:
                return {"signal": False, "reason": "NO_FVG"}
            elif not last['bullish_bias']:
                return {"signal": False, "reason": "BEARISH_BIAS"}
            elif not last['in_session']:
                return {"signal": False, "reason": "OUTSIDE_SESSION"}
            else:
                return {"signal": False, "reason": "UNKNOWN"}
        
        # Signal found
        atr = last['atr']
        entry = last['close']
        sl = entry - (atr * self.params["sl_atr_mult"])
        tp = entry + (atr * self.params["sl_atr_mult"] * self.params["rr_ratio"])
        
        return {
            "signal": True,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "risk_percent": self.params["risk_percent"],  # 0.25
            "risk_fraction": self.params["risk_fraction"],  # 0.0025
            "timestamp": data['timestamp'].iloc[-1].isoformat()
        }
    
    def get_strategy_definition(self) -> Dict:
        """Return complete strategy definition for evidence objects."""
        return {
            "strategy_version": self.strategy_version,
            "pair": self.params["pair"],
            "direction": self.params["direction"],
            "ema_fast": self.params["ema_fast"],
            "ema_slow": self.params["ema_slow"],
            "sl_atr_mult": self.params["sl_atr_mult"],
            "rr_ratio": self.params["rr_ratio"],
            "max_hold_bars": self.params["max_hold_bars"],
            "sessions": self.params["sessions"],
            "risk_percent": self.params["risk_percent"],
            "risk_fraction": self.params["risk_fraction"],
            "frozen": True
        }

# TEST: Verify all components use same implementation
if __name__ == "__main__":
    strategy = CanonicalV4Strategy()
    
    print("="*70)
    print("  CANONICAL V4 STRATEGY")
    print("="*70)
    
    # Show strategy definition
    definition = strategy.get_strategy_definition()
    print(f"\n  Strategy Version: {definition['strategy_version']}")
    print(f"  Pair: {definition['pair']}")
    print(f"  Direction: {definition['direction']}")
    print(f"  Risk: {definition['risk_percent']}% (explicit)")
    print(f"  Risk Fraction: {definition['risk_fraction']} (explicit)")
    print(f"  Frozen: {definition['frozen']}")
    
    # Test backtest
    print(f"\n  Running backtest...")
    data = strategy.load_data()
    trades = strategy.run_backtest(data)
    
    if trades:
        r_values = [t["r"] for t in trades]
        print(f"    Trades: {len(trades)}")
        print(f"    Win rate: {(sum(1 for r in r_values if r > 0) / len(r_values))*100:.1f}%")
        print(f"    Expectancy: {np.mean(r_values):.3f}R")
    
    # Test current signal
    print(f"\n  Checking current signal...")
    signal = strategy.check_current_signal()
    print(f"    Signal: {signal}")


