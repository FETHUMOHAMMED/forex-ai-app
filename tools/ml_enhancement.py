"""ML ENHANCEMENT - Predict TP probability for each setup."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
from pathlib import Path

class MLEnhancer:
    """Predicts P(TP before SL) for each FVG setup."""
    
    def __init__(self):
        self.model = None
        self.feature_columns = []
        self.model_path = Path("research/ml_models")
        self.model_path.mkdir(parents=True, exist_ok=True)
        
    def prepare_training_data(self):
        """Create labeled dataset from historical trades."""
        print("Preparing training data...")
        
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
        mt5.shutdown()
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        # Calculate features
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean()
        data['ema_distance'] = (data['ema_50'] - data['ema_200']) / data['ema_200']
        
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        data['atr_pct'] = data['atr'] / data['close']
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume (if available)
        if 'tick_volume' in data.columns:
            data['volume_ma'] = data['tick_volume'].rolling(20).mean()
            data['volume_ratio'] = data['tick_volume'] / data['volume_ma']
        
        # Session
        data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
        
        # Generate features and labels for each setup
        features_list = []
        labels = []
        
        for i in range(200, len(data)):
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            # Only bullish FVG setups (long-only strategy)
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * 2.0)
                tp = entry + (data['atr'].iloc[i] * 5.0)
                
                # Features at time of setup
                features = {
                    "ema_distance": data['ema_distance'].iloc[i],
                    "atr_pct": data['atr_pct'].iloc[i],
                    "rsi": data['rsi'].iloc[i],
                    "hour": data['hour'].iloc[i],
                    "fvg_size": (data['low'].iloc[i] - data['high'].iloc[i-2]) / data['atr'].iloc[i],
                    "trend_strength": (data['ema_50'].iloc[i] - data['ema_200'].iloc[i]) / data['ema_200'].iloc[i],
                    "candle_range": (data['high'].iloc[i] - data['low'].iloc[i]) / data['atr'].iloc[i],
                    "volume_ratio": data.get('volume_ratio', pd.Series([1] * len(data))).iloc[i] if 'volume_ratio' in data.columns else 1.0,
                }
                
                # Label: Did TP get hit before SL?
                exit_idx = min(i + 50, len(data) - 1)
                label = 0  # Default: SL hit
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        label = 0  # SL hit
                        break
                    elif data['high'].iloc[j] >= tp:
                        label = 1  # TP hit
                        break
                else:
                    # Timeout - use final position
                    exit_price = data['close'].iloc[exit_idx]
                    if exit_price > entry:
                        label = 1  # Profitable timeout
                    else:
                        label = 0  # Losing timeout
                
                features_list.append(features)
                labels.append(label)
        
        if not features_list:
            print("No training data generated")
            return None
        
        X = pd.DataFrame(features_list)
        y = pd.Series(labels)
        
        print(f"Training data: {len(X)} samples")
        print(f"Positive class (TP): {y.sum()} ({y.mean()*100:.1f}%)")
        print(f"Negative class (SL): {(1-y).sum()} ({(1-y).mean()*100:.1f}%)")
        
        return X, y
    
    def train_model(self, X, y):
        """Train ML model to predict P(TP)."""
        print("\nTraining ML model...")
        
        # Split data chronologically (not random!)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=5,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\nModel Performance:")
        print(f"  Training samples: {len(X_train)}")
        print(f"  Test samples: {len(X_test)}")
        print(f"  Accuracy: {accuracy:.3f}")
        print(f"  Baseline (always SL): {(y_test == 0).mean():.3f}")
        print(f"  Baseline (always TP): {(y_test == 1).mean():.3f}")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"\nTop Features:")
        for _, row in feature_importance.head(5).iterrows():
            print(f"  {row['feature']}: {row['importance']:.3f}")
        
        # Save model
        model_file = self.model_path / "fvg_tp_predictor.pkl"
        joblib.dump(self.model, model_file)
        print(f"\nModel saved to {model_file}")
        
        return self.model
    
    def predict_setup(self, features):
        """Predict P(TP) for a new setup."""
        if self.model is None:
            # Load model if not loaded
            model_file = self.model_path / "fvg_tp_predictor.pkl"
            if model_file.exists():
                self.model = joblib.load(model_file)
            else:
                print("No model available")
                return None
        
        features_df = pd.DataFrame([features])
        prob_tp = self.model.predict_proba(features_df)[0, 1]
        return prob_tp
    
    def calculate_expected_value(self, prob_tp, rr_ratio=2.5):
        """Calculate expected value of a trade."""
        prob_sl = 1 - prob_tp
        ev = (prob_tp * rr_ratio) - (prob_sl * 1.0)
        return ev
    
    def should_trade(self, features, min_ev=0.2):
        """Decide whether to trade based on ML prediction."""
        prob_tp = self.predict_setup(features)
        if prob_tp is None:
            return False, 0, 0
        
        ev = self.calculate_expected_value(prob_tp)
        
        # Trade only if expected value is positive
        should_trade = ev > min_ev
        
        return should_trade, prob_tp, ev

if __name__ == "__main__":
    enhancer = MLEnhancer()
    
    # Train the model
    X, y = enhancer.prepare_training_data()
    if X is not None:
        enhancer.feature_columns = X.columns.tolist()
        enhancer.train_model(X, y)
        
        # Example prediction
        example_features = {
            "ema_distance": 0.002,
            "atr_pct": 0.003,
            "rsi": 45,
            "hour": 8,
            "fvg_size": 0.5,
            "trend_strength": 0.002,
            "candle_range": 0.8,
            "volume_ratio": 1.2,
        }
        
        prob_tp = enhancer.predict_setup(example_features)
        ev = enhancer.calculate_expected_value(prob_tp)
        trade_decision, _, _ = enhancer.should_trade(example_features)
        
        print(f"\nExample Setup Prediction:")
        print(f"  P(TP before SL): {prob_tp:.1%}")
        print(f"  Expected value: {ev:.3f}R")
        print(f"  Trade decision: {'TRADE' if trade_decision else 'NO TRADE'}")
