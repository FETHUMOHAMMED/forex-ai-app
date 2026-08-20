"""Strategy focused ONLY on 05:00 UTC (empirically profitable hour)."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def run_0500_strategy():
    """Trade only at 05:00 UTC with momentum filter."""
    print("="*60)
    print("  05:00 UTC FOCUSED STRATEGY")
    print("="*60)
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    # Test on multiple pairs
    results = {}
    
    for symbol in ['USDJPYm', 'EURUSDm', 'GBPUSDm', 'AUDUSDm']:
        print(f"\n{'='*60}")
        print(f"  Testing {symbol}")
        print(f"{'='*60}")
        
        data = all_data[symbol]['M15'].copy()
        
        # Add features
        data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
        data['returns_50'] = data['close'].pct_change(50)
        data['returns_20'] = data['close'].pct_change(20)
        data['returns_10'] = data['close'].pct_change(10)
        
        # Only trade at 05:00 UTC
        data['is_0500'] = data['hour'] == 5
        
        trades = []
        
        for i in range(100, len(data)):
            if not data['is_0500'].iloc[i]:
                continue
            
            # Momentum conditions
            # Long: 50-bar uptrend + recent pullback
            if (data['returns_50'].iloc[i] > 0.001 and 
                data['returns_20'].iloc[i] < 0 and 
                data['returns_10'].iloc[i] < 0):
                
                entry = data['close'].iloc[i]
                # Use ATR for stop
                atr = (data['high'].iloc[i-20:i] - data['low'].iloc[i-20:i]).mean()
                sl = entry - (atr * 1.5)
                tp = entry + (atr * 3.0)  # 2:1 R:R
                
                # Hold for maximum 50 bars
                exit_idx = min(i + 50, len(data) - 1)
                
                # Check SL/TP
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        trades.append({"r": -1, "result": "SL"})
                        break
                    elif data['high'].iloc[j] >= tp:
                        trades.append({"r": 2, "result": "TP"})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    trades.append({"r": r, "result": "TIMEOUT"})
            
            # Short: 50-bar downtrend + recent rally
            elif (data['returns_50'].iloc[i] < -0.001 and 
                  data['returns_20'].iloc[i] > 0 and 
                  data['returns_10'].iloc[i] > 0):
                
                entry = data['close'].iloc[i]
                atr = (data['high'].iloc[i-20:i] - data['low'].iloc[i-20:i]).mean()
                sl = entry + (atr * 1.5)
                tp = entry - (atr * 3.0)
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['high'].iloc[j] >= sl:
                        trades.append({"r": -1, "result": "SL"})
                        break
                    elif data['low'].iloc[j] <= tp:
                        trades.append({"r": 2, "result": "TP"})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (entry - exit_price) / (sl - entry)
                    trades.append({"r": r, "result": "TIMEOUT"})
        
        # Calculate results
        if trades:
            trades_df = pd.DataFrame(trades)
            
            wins = (trades_df['r'] > 0).sum()
            losses = (trades_df['r'] < 0).sum()
            total = len(trades_df)
            
            gross_profit = trades_df[trades_df['r'] > 0]['r'].sum()
            gross_loss = abs(trades_df[trades_df['r'] < 0]['r'].sum())
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            expectancy = trades_df['r'].mean()
            
            print(f"  Trades: {total}")
            print(f"  Win rate: {wins/total*100:.1f}%")
            print(f"  Profit factor: {pf:.3f}")
            print(f"  Expectancy: {expectancy:.3f}R")
            print(f"  Total R: {trades_df['r'].sum():.1f}")
            
            # Monthly consistency
            if len(trades_df) >= 10:
                trades_df['month'] = pd.to_datetime(data['timestamp'].iloc[100:100+len(trades_df)]).dt.to_period('M')
                
                # Track equity curve
                trades_df['cumulative_r'] = trades_df['r'].cumsum()
                
                # Check consistency
                profitable_months = 0
                total_months = 0
                for month, group in trades_df.groupby('month'):
                    total_months += 1
                    if group['r'].sum() > 0:
                        profitable_months += 1
                
                print(f"  Profitable months: {profitable_months}/{total_months}")
            
            results[symbol] = {
                "total_trades": total,
                "win_rate": wins/total,
                "profit_factor": pf,
                "expectancy": expectancy,
                "total_r": trades_df['r'].sum()
            }
        else:
            print(f"  No trades generated")
            results[symbol] = {"total_trades": 0}
    
    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY - 05:00 UTC STRATEGY")
    print(f"{'='*60}")
    for symbol, stats in results.items():
        if stats["total_trades"] > 0:
            print(f"\n{symbol}:")
            print(f"  Trades: {stats['total_trades']}")
            print(f"  Win rate: {stats['win_rate']*100:.1f}%")
            print(f"  PF: {stats['profit_factor']:.3f}")
            print(f"  Expectancy: {stats['expectancy']:.3f}R")
            print(f"  Total R: {stats['total_r']:.1f}")
    
    return results

if __name__ == "__main__":
    results = run_0500_strategy()
