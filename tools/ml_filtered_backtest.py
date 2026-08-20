"""Backtest with ML filter applied."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

def run_ml_filtered_backtest():
    """Compare baseline vs ML-filtered strategy."""
    print("="*60)
    print("  ML-FILTERED BACKTEST")
    print("="*60)
    
    # Load model
    model_path = Path("research/ml_models/fvg_tp_predictor.pkl")
    if not model_path.exists():
        print("No ML model found")
        return None
    
    model = joblib.load(model_path)
    
    # Load data
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
    
    # Run baseline and ML-filtered
    baseline_trades = []
    ml_trades = []
    rejected_trades = []
    
    for i in range(200, len(data)):
        if not (7 <= data['hour'].iloc[i] <= 11):
            continue
        
        if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
            continue
        
        if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * 2.0)
            tp = entry + (data['atr'].iloc[i] * 5.0)
            
            # Features
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
            
            # ML prediction
            features_df = pd.DataFrame([features])
            prob_tp = model.predict_proba(features_df)[0, 1]
            ev = (prob_tp * 2.5) - ((1 - prob_tp) * 1.0)
            
            # Simulate trade
            trade_result = None
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trade_result = -1.0
                    break
                elif data['high'].iloc[j] >= tp:
                    trade_result = 2.5
                    break
            
            if trade_result is None:
                exit_price = data['close'].iloc[exit_idx]
                trade_result = (exit_price - entry) / (entry - sl)
            
            # Baseline takes all trades
            baseline_trades.append(trade_result)
            
            # ML takes only high EV trades
            if ev > 0.2:  # Minimum EV threshold
                ml_trades.append(trade_result)
            else:
                rejected_trades.append({
                    "r": trade_result,
                    "prob_tp": prob_tp,
                    "ev": ev
                })
    
    # Results
    def calc_stats(trades):
        if not trades:
            return {"trades": 0, "win_rate": 0, "pf": 0, "expectancy": 0}
        r_values = trades
        wins = sum(1 for r in r_values if r > 0)
        gross_profit = sum(r for r in r_values if r > 0)
        gross_loss = abs(sum(r for r in r_values if r < 0))
        return {
            "trades": len(r_values),
            "win_rate": wins / len(r_values),
            "pf": gross_profit / gross_loss if gross_loss > 0 else float('inf'),
            "expectancy": np.mean(r_values),
            "total_r": sum(r_values)
        }
    
    baseline_stats = calc_stats(baseline_trades)
    ml_stats = calc_stats(ml_trades)
    
    print(f"\nBaseline (All Setups):")
    print(f"  Trades: {baseline_stats['trades']}")
    print(f"  Win rate: {baseline_stats['win_rate']*100:.1f}%")
    print(f"  PF: {baseline_stats['pf']:.3f}")
    print(f"  Expectancy: {baseline_stats['expectancy']:.3f}R")
    print(f"  Total R: {baseline_stats['total_r']:.1f}")
    
    print(f"\nML-Filtered (EV > 0.2):")
    print(f"  Trades: {ml_stats['trades']}")
    print(f"  Win rate: {ml_stats['win_rate']*100:.1f}%")
    print(f"  PF: {ml_stats['pf']:.3f}")
    print(f"  Expectancy: {ml_stats['expectancy']:.3f}R")
    print(f"  Total R: {ml_stats['total_r']:.1f}")
    
    print(f"\nRejected by ML:")
    if rejected_trades:
        rejected_r = [t["r"] for t in rejected_trades]
        rejected_stats = calc_stats(rejected_r)
        print(f"  Trades rejected: {len(rejected_trades)}")
        print(f"  Their performance: {rejected_stats['expectancy']:.3f}R")
        print(f"  ML correctly rejected: {'YES' if rejected_stats['expectancy'] < 0 else 'NO'}")
    
    print(f"\nImprovement:")
    improvement = ml_stats['expectancy'] - baseline_stats['expectancy']
    print(f"  Expectancy improvement: {improvement:.3f}R")
    if improvement > 0:
        print(f"  ML filter is HELPING")
    else:
        print(f"  ML filter is NOT helping (stick with baseline)")
    
    return {"baseline": baseline_stats, "ml": ml_stats}

if __name__ == "__main__":
    results = run_ml_filtered_backtest()
