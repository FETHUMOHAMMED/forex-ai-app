"""CONTINUOUS PAPER TRADING RUNNER - Automated evaluation loop."""
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timezone

class ContinuousPaperRunner:
    """Runs paper trading automatically at consistent intervals."""
    
    def __init__(self):
        self.log_file = Path("research/paper/V4_CANONICAL_1.0/enhanced_signal_log.jsonl")
        self.check_interval_seconds = 900  # 15 minutes
        self.london_session = (7, 11)
        self.evaluation_count = 0
        
    def should_check_now(self) -> bool:
        """Check if we should evaluate signal now."""
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        current_minute = now.minute
        
        # During London session (7-11 UTC): check every 15 minutes
        if self.london_session[0] <= current_hour < self.london_session[1]:
            return current_minute % 15 == 0
        
        # Outside London: check at top of hour
        return current_minute == 0
    
    def evaluate_signal(self):
        """Evaluate signal using canonical strategy directly."""
        import MetaTrader5 as mt5
        import pandas as pd
        
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
        
        last = data.iloc[-1]
        
        # Check in order
        bullish_fvg = data['high'].iloc[-3] < data['low'].iloc[-1]
        if not bullish_fvg:
            return {
                "signal": False, "reason": "NO_FVG",
                "fvg_detected": False, "bullish_bias": None,
                "london_session": None, "direction_check": "BUY_ONLY"
            }
        
        bullish_bias = last['ema_50'] > last['ema_200']
        if not bullish_bias:
            return {
                "signal": False, "reason": "NO_BULLISH_BIAS",
                "fvg_detected": True, "bullish_bias": False,
                "london_session": None, "direction_check": "BUY_ONLY"
            }
        
        london_session = 7 <= last['hour'] < 11
        if not london_session:
            return {
                "signal": False, "reason": "OUTSIDE_LONDON",
                "fvg_detected": True, "bullish_bias": True,
                "london_session": False, "direction_check": "BUY_ONLY"
            }
        
        # Valid setup
        atr = last['atr']
        entry = last['close']
        sl = entry - (atr * 2.0)
        tp = entry + (atr * 4.0)
        
        return {
            "signal": True, "reason": "VALID_BUY_SETUP",
            "fvg_detected": True, "bullish_bias": True,
            "london_session": True, "direction_check": "BUY_ONLY",
            "entry": entry, "sl": sl, "tp": tp,
            "rr_ratio": 2.0, "risk_percent": 0.25
        }
    
    def run_continuous(self):
        """Run continuous loop."""
        print("="*60)
        print("  CONTINUOUS PAPER TRADER")
        print("="*60)
        print(f"  Strategy: V4_CANONICAL_1.0 (FROZEN)")
        print(f"  London session: 07:00-11:00 UTC")
        print(f"  Check: Every 15 min (London) / 60 min (other)")
        print(f"  Press Ctrl+C to stop")
        print("="*60)
        
        try:
            while True:
                if self.should_check_now():
                    self.evaluation_count += 1
                    result = self.evaluate_signal()
                    
                    # Log result
                    log_entry = {
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "type": "AUTOMATED_CHECK",
                        "evaluation_number": self.evaluation_count,
                        **result
                    }
                    
                    with open(self.log_file, 'a') as f:
                        f.write(json.dumps(log_entry) + '\n')
                    
                    print(f"\n[{datetime.now(timezone.utc).strftime('%H:%M UTC')}] "
                          f"Eval #{self.evaluation_count}: {result.get('reason', 'UNKNOWN')}")
                
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            print(f"\n\nRunner stopped. Total evaluations: {self.evaluation_count}")
            print(f"Log file: {self.log_file}")

if __name__ == "__main__":
    runner = ContinuousPaperRunner()
    runner.run_continuous()
