"""Test strategies on higher timeframes."""
import pandas as pd
import numpy as np
import pickle

def test_higher_timeframes():
    """Test if higher timeframes have more edge."""
    print("="*60)
    print("  HIGHER TIMEFRAME ANALYSIS")
    print("="*60)
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    # Test H1 and H4 timeframes
    for tf in ['H1', 'H4']:
        print(f"\n{'='*60}")
        print(f"  Testing {tf} Timeframe")
        print(f"{'='*60}")
        
        for symbol in ['USDJPYm', 'EURUSDm', 'GBPUSDm', 'AUDUSDm']:
            data = all_data[symbol][tf].copy()
            
            # Calculate returns over different horizons
            print(f"\n{symbol}:")
            for horizon in [1, 5, 10, 20]:
                returns = data['close'].pct_change(horizon).dropna()
                win_rate = (returns > 0).mean() * 100
                avg_win = returns[returns > 0].mean() * 100
                avg_loss = returns[returns < 0].mean() * 100
                net = returns.mean() * 100
                
                print(f"  {horizon}-bar: {win_rate:.0f}% win, net {net:.3f}%")
            
            # Simple momentum test
            data['momentum'] = data['close'].pct_change(10)
            data['returns'] = data['close'].pct_change()
            
            # Test simple breakout
            data['high_20'] = data['high'].rolling(20).max()
            data['low_20'] = data['low'].rolling(20).min()
            
            trades = []
            
            for i in range(20, len(data)):
                # Breakout long
                if data['close'].iloc[i] > data['high_20'].iloc[i-1]:
                    entry = data['close'].iloc[i]
                    sl = entry * 0.99  # 1% stop
                    tp = entry * 1.02  # 2% target
                    
                    for j in range(i+1, min(i+20, len(data))):
                        if data['low'].iloc[j] <= sl:
                            trades.append({"r": -1})
                            break
                        elif data['high'].iloc[j] >= tp:
                            trades.append({"r": 2})
                            break
                    else:
                        exit_price = data['close'].iloc[min(i+20, len(data)-1)]
                        trades.append({"r": (exit_price - entry) / (entry - sl)})
                
                # Breakout short
                elif data['close'].iloc[i] < data['low_20'].iloc[i-1]:
                    entry = data['close'].iloc[i]
                    sl = entry * 1.01
                    tp = entry * 0.98
                    
                    for j in range(i+1, min(i+20, len(data))):
                        if data['high'].iloc[j] >= sl:
                            trades.append({"r": -1})
                            break
                        elif data['low'].iloc[j] <= tp:
                            trades.append({"r": 2})
                            break
                    else:
                        exit_price = data['close'].iloc[min(i+20, len(data)-1)]
                        trades.append({"r": (entry - exit_price) / (sl - entry)})
            
            if trades:
                trades_df = pd.DataFrame(trades)
                wins = (trades_df['r'] > 0).sum()
                total = len(trades_df)
                gross_profit = trades_df[trades_df['r'] > 0]['r'].sum()
                gross_loss = abs(trades_df[trades_df['r'] < 0]['r'].sum())
                pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                expectancy = trades_df['r'].mean()
                
                print(f"\n  Breakout Strategy:")
                print(f"    Trades: {total}")
                print(f"    Win rate: {wins/total*100:.0f}%")
                print(f"    PF: {pf:.3f}")
                print(f"    Expectancy: {expectancy:.3f}R")

if __name__ == "__main__":
    test_higher_timeframes()
