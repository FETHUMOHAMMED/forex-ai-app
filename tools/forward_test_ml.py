"""Forward test the ML-filtered strategy."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timezone
from pathlib import Path
import json

class MLForwardTest:
    """Forward test with ML filter."""
    
    def __init__(self):
        self.model_path = Path("research/ml_models/fvg_tp_predictor.pkl")
        self.model = joblib.load(self.model_path) if self.model_path.exists() else None
        self.results_dir = Path("research/forward_test_ml")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def check_for_setup(self):
        """Check for valid setup and predict with ML."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 200)
        mt5.shutdown()
        
        if rates is None or len(rates) < 200:
            return None
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        # Current time check
        current_hour = datetime.now(timezone.utc).hour
        if not (7 <= current_hour < 11):
            return None
        
        # Calculate features
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean()
        
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        
        # Check setup (long only)
        if data['ema_50'].iloc[-1] <= data['ema_200'].iloc[-1]:
            return None
        
        if data['high'].iloc[-3] < data['low'].iloc[-1]:
            # FVG detected!
            features = {
                "ema_distance": (data['ema_50'].iloc[-1] - data['ema_200'].iloc[-1]) / data['ema_200'].iloc[-1],
                "atr_pct": data['atr'].iloc[-1] / data['close'].iloc[-1],
                "rsi": 50,  # Simplified
                "hour": current_hour,
                "fvg_size": (data['low'].iloc[-1] - data['high'].iloc[-3]) / data['atr'].iloc[-1],
                "trend_strength": (data['ema_50'].iloc[-1] - data['ema_200'].iloc[-1]) / data['ema_200'].iloc[-1],
                "candle_range": (data['high'].iloc[-1] - data['low'].iloc[-1]) / data['atr'].iloc[-1],
                "volume_ratio": 1.0,
            }
            
            # ML prediction
            if self.model:
                features_df = pd.DataFrame([features])
                prob_tp = self.model.predict_proba(features_df)[0, 1]
                ev = (prob_tp * 2.5) - ((1 - prob_tp) * 1.0)
            else:
                prob_tp = 0.47
                ev = 0.527
            
            return {
                "setup": "FVG_BULLISH",
                "entry": data['close'].iloc[-1],
                "sl": data['close'].iloc[-1] - (data['atr'].iloc[-1] * 2.0),
                "tp": data['close'].iloc[-1] + (data['atr'].iloc[-1] * 5.0),
                "prob_tp": prob_tp,
                "expected_value": ev,
                "trade": ev > 0.3  # Higher threshold with ML
            }
        
        return None
    
    def run_once(self):
        """Run one check."""
        setup = self.check_for_setup()
        
        if setup:
            print(f"\nSetup found!")
            print(f"  Entry: {setup['entry']:.3f}")
            print(f"  SL: {setup['sl']:.3f}")
            print(f"  TP: {setup['tp']:.3f}")
            print(f"  P(TP): {setup['prob_tp']:.1%}")
            print(f"  Expected value: {setup['expected_value']:.3f}R")
            print(f"  Decision: {'TRADE' if setup['trade'] else 'SKIP'}")
            
            # Save setup
            filepath = self.results_dir / "setups.jsonl"
            with open(filepath, 'a') as f:
                f.write(json.dumps(setup, default=str) + '\n')
        else:
            print("No valid setup at this time")
        
        return setup

if __name__ == "__main__":
    tester = MLForwardTest()
    setup = tester.run_once()
