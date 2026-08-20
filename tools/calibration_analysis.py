"""PROBABILITY CALIBRATION ANALYSIS - Is our ML model honest?"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss
import json

class CalibrationAnalyzer:
    """Analyzes if ML probabilities are well-calibrated."""
    
    def __init__(self):
        self.model_path = Path("research/ml_models/fvg_tp_predictor.pkl")
        self.model = joblib.load(self.model_path) if self.model_path.exists() else None
        
    def prepare_data(self):
        """Prepare data with features and labels."""
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
        
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
        
        if 'tick_volume' in data.columns:
            data['volume_ma'] = data['tick_volume'].rolling(20).mean()
            data['volume_ratio'] = data['tick_volume'] / data['volume_ma']
        else:
            data['volume_ratio'] = 1.0
        
        # Generate features and labels
        features_list = []
        labels = []
        
        for i in range(200, len(data)):
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * 2.0)
                tp = entry + (data['atr'].iloc[i] * 5.0)
                
                features = {
                    "ema_distance": data['ema_distance'].iloc[i],
                    "atr_pct": data['atr_pct'].iloc[i],
                    "rsi": data['rsi'].iloc[i],
                    "hour": data['hour'].iloc[i],
                    "fvg_size": (data['low'].iloc[i] - data['high'].iloc[i-2]) / data['atr'].iloc[i],
                    "trend_strength": (data['ema_50'].iloc[i] - data['ema_200'].iloc[i]) / data['ema_200'].iloc[i],
                    "candle_range": (data['high'].iloc[i] - data['low'].iloc[i]) / data['atr'].iloc[i],
                    "volume_ratio": data['volume_ratio'].iloc[i],
                }
                
                # Label
                exit_idx = min(i + 50, len(data) - 1)
                label = 0
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        label = 0
                        break
                    elif data['high'].iloc[j] >= tp:
                        label = 1
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    label = 1 if exit_price > entry else 0
                
                features_list.append(features)
                labels.append(label)
        
        return pd.DataFrame(features_list), pd.Series(labels)
    
    def analyze_calibration(self, X, y):
        """Analyze probability calibration."""
        print("="*70)
        print("  PROBABILITY CALIBRATION ANALYSIS")
        print("="*70)
        
        if self.model is None:
            print("No model loaded")
            return None
        
        # Get predicted probabilities
        probas = self.model.predict_proba(X)[:, 1]
        
        # Brier score (lower is better, 0.25 = random)
        brier = brier_score_loss(y, probas)
        print(f"\n1. BRIER SCORE")
        print(f"   Score: {brier:.4f}")
        print(f"   Interpretation: {'Good' if brier < 0.2 else 'Fair' if brier < 0.25 else 'Poor'}")
        print(f"   (0 = perfect, 0.25 = random, >0.25 = worse than random)")
        
        # Calibration curve
        print(f"\n2. RELIABILITY CURVE")
        print(f"   Confidence    Predicted    Actual    Difference")
        print(f"   " + "-"*50)
        
        # Create confidence buckets
        buckets = [(0.3, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]
        
        calibration_data = []
        
        for low, high in buckets:
            mask = (probas >= low) & (probas < high)
            bucket_probas = probas[mask]
            bucket_labels = y[mask]
            
            if len(bucket_labels) >= 3:  # Minimum 3 samples for meaningful stats
                mean_pred = bucket_probas.mean()
                actual_rate = bucket_labels.mean()
                
                calibration_data.append({
                    "bucket": f"{low:.1f}-{high:.1f}",
                    "n": len(bucket_labels),
                    "predicted": mean_pred,
                    "actual": actual_rate,
                    "difference": actual_rate - mean_pred
                })
                
                print(f"   {low:.1f}-{high:.1f}    {mean_pred:.1%}    {actual_rate:.1%}    {actual_rate-mean_pred:+.1%}")
            else:
                print(f"   {low:.1f}-{high:.1f}    (insufficient data: {len(bucket_labels)} samples)")
        
        # Calculate calibration error (ECE - Expected Calibration Error)
        if calibration_data:
            ece = np.mean([abs(d["difference"]) for d in calibration_data])
            print(f"\n3. EXPECTED CALIBRATION ERROR (ECE)")
            print(f"   ECE: {ece:.4f}")
            print(f"   Interpretation: {'Excellent' if ece < 0.05 else 'Good' if ece < 0.1 else 'Fair' if ece < 0.15 else 'Poor'}")
        
        # Precision by confidence bucket
        print(f"\n4. PRECISION BY CONFIDENCE BUCKET")
        for d in calibration_data:
            print(f"   {d['bucket']}: {d['n']} trades, {d['actual']:.1%} actual win rate")
        
        # Key insights
        print(f"\n5. KEY INSIGHTS")
        
        if calibration_data:
            # Check if higher confidence = higher actual win rate
            predicted_rates = [d["predicted"] for d in calibration_data]
            actual_rates = [d["actual"] for d in calibration_data]
            
            if len(predicted_rates) >= 2:
                correlation = np.corrcoef(predicted_rates, actual_rates)[0, 1]
                print(f"   Correlation (predicted vs actual): {correlation:.3f}")
                
                if correlation > 0.7:
                    print(f"   Model is well-ranked (higher confidence = higher win rate)")
                elif correlation > 0.3:
                    print(f"   Model has some ranking ability")
                else:
                    print(f"   Model has poor ranking ability")
            
            # Check for overconfidence
            avg_pred = np.mean([d["predicted"] for d in calibration_data])
            avg_actual = np.mean([d["actual"] for d in calibration_data])
            
            print(f"\n   Average predicted: {avg_pred:.1%}")
            print(f"   Average actual: {avg_actual:.1%}")
            
            if avg_pred > avg_actual + 0.1:
                print(f"   MODEL IS OVERCONFIDENT (predicts higher than reality)")
            elif avg_pred < avg_actual - 0.1:
                print(f"   MODEL IS UNDERCONFIDENT (predicts lower than reality)")
            else:
                print(f"   Model is reasonably calibrated")
        
        # How to use this information
        print(f"\n6. PRACTICAL IMPLICATIONS")
        print(f"   If model is overconfident:")
        print(f"   - Reduce position size for high-confidence trades")
        print(f"   - Use actual win rates, not predicted probabilities")
        print(f"   - Adjust EV threshold based on calibration")
        
        print(f"\n   Recommended EV calculation (using calibrated probabilities):")
        
        for d in calibration_data:
            if d["n"] >= 5:
                calibrated_ev = (d["actual"] * 2.5) - ((1 - d["actual"]) * 1.0)
                raw_ev = (d["predicted"] * 2.5) - ((1 - d["predicted"]) * 1.0)
                print(f"   {d['bucket']}: Raw EV {raw_ev:.2f}R, Calibrated EV {calibrated_ev:.2f}R")
        
        return calibration_data
    
    def run_full_analysis(self):
        """Run complete calibration analysis."""
        X, y = self.prepare_data()
        if X is None:
            return None
        
        calibration_results = self.analyze_calibration(X, y)
        
        # Save results
        results_path = Path("research/calibration_results.json")
        with open(results_path, 'w') as f:
            json.dump(calibration_results, f, indent=2, default=str)
        
        print(f"\nResults saved to {results_path}")
        
        return calibration_results

if __name__ == "__main__":
    analyzer = CalibrationAnalyzer()
    results = analyzer.run_full_analysis()
