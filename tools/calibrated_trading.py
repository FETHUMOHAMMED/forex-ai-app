"""CALIBRATED TRADING - Using honest probabilities."""
import joblib
import pandas as pd
from pathlib import Path

class CalibratedTrading:
    """Trade using calibrated probabilities instead of raw ML outputs."""
    
    def __init__(self):
        self.model_path = Path("research/ml_models/fvg_tp_predictor.pkl")
        self.model = joblib.load(self.model_path) if self.model_path.exists() else None
        
        # Calibration mapping (from our analysis)
        self.calibration_map = {
            (0.30, 0.40): {"actual_prob": 0.00, "ev": -1.00, "trade": False},
            (0.40, 0.50): {"actual_prob": 0.27, "ev": -0.05, "trade": False},
            (0.50, 0.60): {"actual_prob": 0.61, "ev": 1.12, "trade": True},
            (0.60, 0.70): {"actual_prob": 0.81, "ev": 1.83, "trade": True},
            (0.70, 0.80): {"actual_prob": 0.92, "ev": 2.21, "trade": True},
        }
        
    def get_calibrated_probability(self, raw_prob):
        """Convert raw ML probability to calibrated probability."""
        for (low, high), data in self.calibration_map.items():
            if low <= raw_prob < high:
                return data["actual_prob"], data["ev"], data["trade"]
        
        # Default for out-of-range
        if raw_prob < 0.30:
            return 0.0, -1.0, False
        elif raw_prob >= 0.80:
            return 0.95, 2.5, True
        
        return raw_prob, (raw_prob * 2.5) - (1 - raw_prob), True
    
    def make_decision(self, features):
        """Make trading decision with calibrated probabilities."""
        if self.model is None:
            return {
                "decision": "NO_MODEL",
                "raw_probability": None,
                "calibrated_probability": None,
                "expected_value": None,
                "trade": False
            }
        
        # Get raw prediction
        features_df = pd.DataFrame([features])
        raw_prob = self.model.predict_proba(features_df)[0, 1]
        
        # Calibrate
        calibrated_prob, ev, trade = self.get_calibrated_probability(raw_prob)
        
        return {
            "decision": "TRADE" if trade else "NO_TRADE",
            "raw_probability": raw_prob,
            "calibrated_probability": calibrated_prob,
            "expected_value": ev,
            "trade": trade
        }
    
    def calculate_position_size(self, account_balance, risk_pct, features):
        """Calculate position size using calibrated probabilities."""
        decision = self.make_decision(features)
        
        if not decision["trade"]:
            return {"risk_amount": 0, "risk_pct": 0, "confidence": 0}
        
        # Use calibrated probability to adjust risk
        # Higher confidence = can risk slightly more (but cap at 0.75%)
        confidence_adjustment = decision["calibrated_probability"] / 0.60
        adjusted_risk = min(risk_pct * confidence_adjustment, risk_pct * 1.5)
        
        risk_amount = account_balance * (adjusted_risk / 100)
        
        return {
            "risk_amount": risk_amount,
            "risk_pct": adjusted_risk,
            "confidence": decision["calibrated_probability"]
        }

if __name__ == "__main__":
    trader = CalibratedTrading()
    
    # Example features
    features = {
        "ema_distance": 0.002,
        "atr_pct": 0.003,
        "rsi": 45,
        "hour": 8,
        "fvg_size": 0.5,
        "trend_strength": 0.002,
        "candle_range": 0.8,
        "volume_ratio": 1.2,
    }
    
    decision = trader.make_decision(features)
    
    print("="*60)
    print("  CALIBRATED TRADING DECISION")
    print("="*60)
    print(f"  Raw ML probability: {decision['raw_probability']:.1%}")
    print(f"  Calibrated probability: {decision['calibrated_probability']:.1%}")
    print(f"  Expected value: {decision['expected_value']:.3f}R")
    print(f"  Decision: {decision['decision']}")
    
    # Position sizing example
    sizing = trader.calculate_position_size(5000, 0.5, features)
    print(f"\n  Position sizing (5,000 account):")
    print(f"  Risk amount: ${sizing['risk_amount']:.2f}")
    print(f"  Risk percentage: {sizing['risk_pct']:.2f}%")

