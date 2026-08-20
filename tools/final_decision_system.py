"""FINAL INTEGRATED DECISION SYSTEM - All layers combined."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timezone
from pathlib import Path
import json

class FinalDecisionSystem:
    """Complete trading decision system with all layers."""
    
    def __init__(self):
        # Load ML model
        self.model_path = Path("research/ml_models/fvg_tp_predictor.pkl")
        self.model = joblib.load(self.model_path) if self.model_path.exists() else None
        
        # Calibration map
        self.calibration = {
            (0.30, 0.40): {"actual": 0.00, "trade": False},
            (0.40, 0.50): {"actual": 0.27, "trade": False},
            (0.50, 0.60): {"actual": 0.61, "trade": True},
            (0.60, 0.70): {"actual": 0.81, "trade": True},
            (0.70, 0.80): {"actual": 0.92, "trade": True},
        }
        
    def check_setup(self):
        """Check for valid FVG setup."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 200)
        mt5.shutdown()
        
        if rates is None or len(rates) < 200:
            return None
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        # Session check
        current_hour = datetime.now(timezone.utc).hour
        if not (7 <= current_hour < 11):
            return {"status": "OUTSIDE_SESSION", "hour": current_hour}
        
        # Calculate indicators
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean()
        
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        
        # Bias check (long only)
        if data['ema_50'].iloc[-1] <= data['ema_200'].iloc[-1]:
            return {"status": "BEARISH_BIAS", "message": "No trade - bearish bias"}
        
        # FVG check
        if data['high'].iloc[-3] >= data['low'].iloc[-1]:
            return {"status": "NO_FVG", "message": "No FVG setup detected"}
        
        # Valid setup found!
        entry = data['close'].iloc[-1]
        atr = data['atr'].iloc[-1]
        sl = entry - (atr * 2.0)
        tp = entry + (atr * 5.0)
        
        # Features for ML
        features = {
            "ema_distance": (data['ema_50'].iloc[-1] - data['ema_200'].iloc[-1]) / data['ema_200'].iloc[-1],
            "atr_pct": atr / entry,
            "rsi": 50,
            "hour": current_hour,
            "fvg_size": (data['low'].iloc[-1] - data['high'].iloc[-3]) / atr,
            "trend_strength": (data['ema_50'].iloc[-1] - data['ema_200'].iloc[-1]) / data['ema_200'].iloc[-1],
            "candle_range": (data['high'].iloc[-1] - data['low'].iloc[-1]) / atr,
            "volume_ratio": 1.0,
        }
        
        # ML prediction
        raw_prob = None
        if self.model:
            features_df = pd.DataFrame([features])
            raw_prob = self.model.predict_proba(features_df)[0, 1]
        
        # Calibrate
        calibrated_prob = raw_prob
        trade_decision = False
        ev = 0
        
        if raw_prob is not None:
            for (low, high), cal in self.calibration.items():
                if low <= raw_prob < high:
                    calibrated_prob = cal["actual"]
                    trade_decision = cal["trade"]
                    ev = (calibrated_prob * 2.5) - ((1 - calibrated_prob) * 1.0)
                    break
        
        return {
            "status": "SETUP_FOUND",
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "raw_probability": raw_prob,
            "calibrated_probability": calibrated_prob,
            "expected_value": ev,
            "trade": trade_decision,
            "reason": "TRADE" if trade_decision else "LOW_PROBABILITY"
        }
    
    def execute_paper_trade(self, setup):
        """Execute paper trade with full documentation."""
        trade = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry": setup["entry"],
            "sl": setup["sl"],
            "tp": setup["tp"],
            "raw_probability": setup["raw_probability"],
            "calibrated_probability": setup["calibrated_probability"],
            "expected_value": setup["expected_value"],
            "status": "OPEN"
        }
        
        # Save trade
        filepath = Path("research/forward_test/trades.jsonl")
        with open(filepath, 'a') as f:
            f.write(json.dumps(trade) + '\n')
        
        return trade

if __name__ == "__main__":
    system = FinalDecisionSystem()
    result = system.check_setup()
    
    print("="*60)
    print("  FINAL DECISION SYSTEM")
    print("="*60)
    
    if result["status"] == "OUTSIDE_SESSION":
        print(f"  Status: Outside London session")
        print(f"  Current hour: {result['hour']}:00 UTC")
        print(f"  London session: 07:00-11:00 UTC")
    elif result["status"] == "BEARISH_BIAS":
        print(f"  Status: Bearish bias")
        print(f"  {result['message']}")
    elif result["status"] == "NO_FVG":
        print(f"  Status: No FVG setup")
        print(f"  {result['message']}")
    elif result["status"] == "SETUP_FOUND":
        print(f"  Status: FVG SETUP FOUND!")
        print(f"  Entry: {result['entry']:.3f}")
        print(f"  SL: {result['sl']:.3f}")
        print(f"  TP: {result['tp']:.3f}")
        print(f"  Raw probability: {result['raw_probability']:.1%}")
        print(f"  Calibrated probability: {result['calibrated_probability']:.1%}")
        print(f"  Expected value: {result['expected_value']:.3f}R")
        print(f"  Decision: {result['trade']}")
        print(f"  Reason: {result['reason']}")
    else:
        print(f"  Status: {result['status']}")
