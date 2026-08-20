"""Optimized AUDUSDm 05:00 UTC strategy."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def run_audusd_optimized():
    """Test variations of AUDUSD 05:00 UTC strategy."""
    print("="*60)
    print("  AUDUSDm 05:00 UTC - OPTIMIZATION")
    print("="*60)
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    data = all_data['AUDUSDm']['M15'].copy()
    
    # Add features
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    data['returns_50'] = data['close'].pct_change(50)
    data['returns_20'] = data['close'].pct_change(20)
    data['returns_10'] = data['close'].pct_change(10)
    data['returns_5'] = data['close'].pct_change(5)
    
    # ATR
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(window=14, min_periods=1).mean()
    
    # Test different parameter combinations
    variations = [
        {"name": "Original", "rr": 2.0, "sl_mult": 1.5, "trend_min": 0.001},
        {"name": "Tighter SL", "rr": 1.5, "sl_mult": 1.0, "trend_min": 0.001},
        {"name": "Wider SL", "rr": 2.5, "sl_mult": 2.0, "trend_min": 0.001},
        {"name": "Stronger trend", "rr": 2.0, "sl_mult": 1.5, "trend_min": 0.002},
        {"name": "Weaker trend", "rr": 2.0, "sl_mult": 1.5, "trend_min": 0.0005},
    ]
    
    results = []
    
    for var in variations:
        trades = []
        
        for i in range(100, len(data)):
            if data['hour'].iloc[i] != 5:
                continue
            
            # Long conditions
            if (data['returns_50'].iloc[i] > var['trend_min'] and 
                data['returns_20'].iloc[i] < 0):
                
                entry = data['close'].iloc[i]
                atr = data['atr'].iloc[i]
                sl = entry - (atr * var['sl_mult'])
                tp = entry + (atr * var['sl_mult'] * var['rr'])
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        trades.append({"r": -1, "result": "SL"})
                        break
                    elif data['high'].iloc[j] >= tp:
                        trades.append({"r": var['rr'], "result": "TP"})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    trades.append({"r": r, "result": "TIMEOUT"})
            
            # Short conditions
            elif (data['returns_50'].iloc[i] < -var['trend_min'] and 
                  data['returns_20'].iloc[i] > 0):
                
                entry = data['close'].iloc[i]
                atr = data['atr'].iloc[i]
                sl = entry + (atr * var['sl_mult'])
                tp = entry - (atr * var['sl_mult'] * var['rr'])
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['high'].iloc[j] >= sl:
                        trades.append({"r": -1, "result": "SL"})
                        break
                    elif data['low'].iloc[j] <= tp:
                        trades.append({"r": var['rr'], "result": "TP"})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (entry - exit_price) / (sl - entry)
                    trades.append({"r": r, "result": "TIMEOUT"})
        
        if trades:
            trades_df = pd.DataFrame(trades)
            
            wins = (trades_df['r'] > 0).sum()
            total = len(trades_df)
            gross_profit = trades_df[trades_df['r'] > 0]['r'].sum()
            gross_loss = abs(trades_df[trades_df['r'] < 0]['r'].sum())
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            expectancy = trades_df['r'].mean()
            
            results.append({
                "name": var['name'],
                "trades": total,
                "win_rate": wins/total,
                "pf": pf,
                "expectancy": expectancy,
                "total_r": trades_df['r'].sum()
            })
            
            print(f"\n{var['name']}:")
            print(f"  Trades: {total}")
            print(f"  Win rate: {wins/total*100:.1f}%")
            print(f"  PF: {pf:.3f}")
            print(f"  Expectancy: {expectancy:.3f}R")
            print(f"  Total R: {trades_df['r'].sum():.1f}")
        else:
            print(f"\n{var['name']}: No trades")
    
    # Find best variation
    if results:
        best = max(results, key=lambda x: x['expectancy'])
        print(f"\n{'='*60}")
        print(f"  BEST: {best['name']}")
        print(f"{'='*60}")
        print(f"  Expectancy: {best['expectancy']:.3f}R")
        print(f"  Profit Factor: {best['pf']:.3f}")
        print(f"  Win Rate: {best['win_rate']*100:.1f}%")
        print(f"  Total Trades: {best['trades']}")
    
    return results

if __name__ == "__main__":
    results = run_audusd_optimized()
