"""
ML Inference - Load models and make predictions.
Replaces the placeholder that always returned None.
"""
import sys, os, pickle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
from ml.feature_engineering import engineer_features, FEATURE_COLUMNS

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')

class MLPredictor:
    """Loads trained models and makes predictions."""
    
    def __init__(self):
        self.models: Dict[str, object] = {}
        self._load_all()
    
    def _load_all(self):
        """Load all .pkl models from models/ directory"""
        if not os.path.exists(MODEL_DIR):
            print(f"[ML] Model directory not found: {MODEL_DIR}")
            return
        
        for f in os.listdir(MODEL_DIR):
            if f.endswith('.pkl'):
                pair = f.replace('.pkl', '')
                try:
                    with open(os.path.join(MODEL_DIR, f), 'rb') as fh:
                        self.models[pair] = pickle.load(fh)
                    print(f"[ML] Loaded {pair}")
                except Exception as e:
                    print(f"[ML] Failed to load {pair}: {e}")
        
        print(f"[ML] {len(self.models)} models loaded: {list(self.models.keys())}")
    
    def predict(self, pair: str, df: pd.DataFrame) -> Tuple[Optional[str], float]:
        """
        Make prediction for a pair.
        Returns (signal, confidence) or (None, 0.5) if no model.
        """
        if pair not in self.models:
            return None, 0.5
        
        try:
            # Engineer features
            features = engineer_features(df)
            if len(features) < 1:
                return None, 0.5
            
            X = features[FEATURE_COLUMNS].iloc[-1:].values
            
            model = self.models[pair]
            proba = model.predict_proba(X)[0]
            pred = model.predict(X)[0]
            
            signal = 'BUY' if pred == 1 else 'SELL'
            confidence = float(proba[1] if pred == 1 else proba[0])
            
            return signal, round(confidence, 3)
        except Exception as e:
            print(f"[ML] Prediction error {pair}: {e}")
            return None, 0.5
    
    def has_model(self, pair: str) -> bool:
        return pair in self.models


# Singleton
predictor = MLPredictor()

if __name__ == '__main__':
    import MetaTrader5 as mt5
    mt5.initialize()
    
    for pair in ['EURUSD', 'GBPUSD', 'USDJPY']:
        if predictor.has_model(pair):
            symbol = pair + 'm'
            mt5.symbol_select(symbol, True)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
            if rates is not None:
                df = pd.DataFrame(rates)
                df.rename(columns={'tick_volume': 'volume'}, inplace=True)
                signal, conf = predictor.predict(pair, df)
                print(f"{pair}: {signal} conf={conf:.3f}")
    
    mt5.shutdown()
