"""Test if mean reversion works better than trend following."""
import pandas as pd
import numpy as np
import pickle

def test_mean_reversion():
    """Test mean reversion strategy."""
    print("Testing mean reversion strategy...")
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    data = all_data['USDJPYm']['M15'].copy()
    
    # Calculate Bollinger Bands
    data['sma'] = data['close'].rolling(window=20).mean()
    data['std'] = data['close'].rolling(window=20).std()
    data['upper'] = data['sma'] + (2 * data['std'])
    data['lower'] = data['sma'] - (2 * data['std'])
    
    # RSI
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # Generate mean reversion signals
    trades = []
    
    for i in range(50, len(data)):
        # Oversold conditions
        if data['rsi'].iloc[i] < 30 and data['close'].iloc[i] < data['lower'].iloc[i]:
            entry = data['close'].iloc[i]
            sl = entry - (data['std'].iloc[i] * 0.5)
            tp = entry + (data['std'].iloc[i] * 1.5)  # Target SMA
            
            for j in range(i+1, min(i+50, len(data))):
                if data['low'].iloc[j] <= sl:
                    trades.append({"result": "LOSS", "r": -1})
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({"result": "WIN", "r": 1.5})
                    break
            else:
                exit_price = data['close'].iloc[min(i+50, len(data)-1)]
                r = (exit_price - entry) / (entry - sl)
                trades.append({"result": "TIMEOUT", "r": r})
        
        # Overbought conditions
        elif data['rsi'].iloc[i] > 70 and data['close'].iloc[i] > data['upper'].iloc[i]:
            entry = data['close'].iloc[i]
            sl = entry + (data['std'].iloc[i] * 0.5)
            tp = entry - (data['std'].iloc[i] * 1.5)
            
            for j in range(i+1, min(i+50, len(data))):
                if data['high'].iloc[j] >= sl:
                    trades.append({"result": "LOSS", "r": -1})
                    break
                elif data['low'].iloc[j] <= tp:
                    trades.append({"result": "WIN", "r": 1.5})
                    break
            else:
                exit_price = data['close'].iloc[min(i+50, len(data)-1)]
                r = (entry - exit_price) / (sl - entry)
                trades.append({"result": "TIMEOUT", "r": r})
    
    # Results
    if trades:
        wins = sum(1 for t in trades if t['r'] > 0)
        total = len(trades)
        win_rate = wins / total * 100
        
        gross_profit = sum(t['r'] for t in trades if t['r'] > 0)
        gross_loss = abs(sum(t['r'] for t in trades if t['r'] < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        expectancy = np.mean([t['r'] for t in trades])
        
        print(f"\nMean Reversion Results:")
        print(f"  Total trades: {total}")
        print(f"  Win rate: {win_rate:.1f}%")
        print(f"  Profit factor: {pf:.3f}")
        print(f"  Expectancy: {expectancy:.3f}R")
        
        if pf > 1.3 and total > 30:
            print("\n  ? Mean reversion shows promise!")
        else:
            print("\n  ? Mean reversion not profitable either")
    
    return trades

if __name__ == "__main__":
    trades = test_mean_reversion()
