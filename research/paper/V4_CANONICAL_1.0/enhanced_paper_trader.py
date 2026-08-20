"""ENHANCED PAPER TRADER - Logs EVERY evaluation with detailed reasons."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import json

class EnhancedPaperTrader:
    """Logs complete signal evaluation with denominator tracking."""
    
    def __init__(self):
        self.log_file = Path("research/paper/V4_CANONICAL_1.0/enhanced_signal_log.jsonl")
        self.strategy_version = "V4_CANONICAL_1.0"
        
    def evaluate_signal(self):
        """Evaluate signal with DETAILED reason codes."""
        if not mt5.initialize():
            return {"signal": False, "reason": "MT5_INIT_FAILED"}
        
        rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 200)
        mt5.shutdown()
        
        if rates is None or len(rates) < 200:
            return {"signal": False, "reason": "INSUFFICIENT_DATA"}
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        # Calculate indicators
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean()
        
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
        
        # Check conditions IN ORDER (matching backtest)
        last = data.iloc[-1]
        
        # 1. FVG check
        bullish_fvg = data['high'].iloc[-3] < data['low'].iloc[-1]
        if not bullish_fvg:
            return self.log_evaluation({
                "signal": False,
                "reason": "NO_FVG",
                "fvg_detected": False,
                "bullish_bias": None,
                "london_session": None,
                "direction_check": "BUY_ONLY"
            })
        
        # 2. Bullish bias check
        bullish_bias = last['ema_50'] > last['ema_200']
        if not bullish_bias:
            return self.log_evaluation({
                "signal": False,
                "reason": "NO_BULLISH_BIAS",
                "fvg_detected": True,
                "bullish_bias": False,
                "london_session": None,
                "direction_check": "BUY_ONLY"
            })
        
        # 3. London session check
        london_session = 7 <= last['hour'] < 11
        if not london_session:
            return self.log_evaluation({
                "signal": False,
                "reason": "OUTSIDE_LONDON",
                "fvg_detected": True,
                "bullish_bias": True,
                "london_session": False,
                "direction_check": "BUY_ONLY"
            })
        
        # 4. All checks passed ? BUY
        atr = last['atr']
        entry = last['close']
        sl = entry - (atr * 2.0)
        tp = entry + (atr * 4.0)
        
        return self.log_evaluation({
            "signal": True,
            "reason": "VALID_BUY_SETUP",
            "fvg_detected": True,
            "bullish_bias": True,
            "london_session": True,
            "direction_check": "BUY_ONLY",
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr_ratio": 2.0,
            "risk_percent": 0.25,
            "risk_fraction": 0.0025
        })
    
    def log_evaluation(self, evaluation: dict) -> dict:
        """Log EVERY evaluation with timestamp."""
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "strategy_version": self.strategy_version,
            **evaluation
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    def run_once(self):
        """Run one evaluation."""
        result = self.evaluate_signal()
        
        print("="*60)
        print("  ENHANCED PAPER TRADER")
        print("="*60)
        print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Strategy: {self.strategy_version} (FROZEN)")
        print(f"  Filters: 4 (FVG ? Bias ? London ? BUY)")
        
        print(f"\n  EVALUATION RESULT:")
        print(f"    Signal: {result.get('signal', False)}")
        print(f"    Reason: {result.get('reason', 'UNKNOWN')}")
        
        if result.get('signal'):
            print(f"    Entry: {result['entry']:.3f}")
            print(f"    SL: {result['sl']:.3f}")
            print(f"    TP: {result['tp']:.3f}")
            print(f"    Risk: {result['risk_percent']}%")
        
        print(f"\n  Logged: {self.log_file}")
        
        return result

if __name__ == "__main__":
    trader = EnhancedPaperTrader()
    trader.run_once()
