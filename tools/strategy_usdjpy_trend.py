"""Strategy designed for USDJPYm trend following."""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

def run_usdjpy_strategy():
    """Run trend-following strategy on USDJPYm."""
    print("="*60)
    print("  USDJPYm TREND STRATEGY")
    print("="*60)
    
    # Load data
    with open('data/research/mt5_historical_data.pkl', 'rb') as f:
        all_data = pickle.load(f)
    
    # Use USDJPYm
    data = all_data['USDJPYm']['M5'].copy()
    
    print(f"\nData: {len(data)} bars")
    print(f"Period: {data['timestamp'].min()} to {data['timestamp'].max()}")
    
    # Calculate indicators
    print("\nCalculating indicators...")
    
    # EMAs for trend
    data['ema_20'] = data['close'].ewm(span=20, min_periods=20).mean()
    data['ema_50'] = data['close'].ewm(span=50, min_periods=50).mean()
    data['ema_200'] = data['close'].ewm(span=200, min_periods=200).mean()
    
    # ATR for volatility
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(window=14, min_periods=1).mean()
    
    # RSI for overbought/oversold
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # Generate signals
    print("\nGenerating signals...")
    trades = []
    
    for i in range(200, len(data)):
        # Trend conditions
        strong_uptrend = (
            data['ema_20'].iloc[i] > data['ema_50'].iloc[i] > data['ema_200'].iloc[i] and
            data['close'].iloc[i] > data['ema_20'].iloc[i]
        )
        
        strong_downtrend = (
            data['ema_20'].iloc[i] < data['ema_50'].iloc[i] < data['ema_200'].iloc[i] and
            data['close'].iloc[i] < data['ema_20'].iloc[i]
        )
        
        # Entry conditions
        if strong_uptrend and data['rsi'].iloc[i] < 40:
            # Pullback in uptrend
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * 1.5)
            tp = entry + (data['atr'].iloc[i] * 3.0)  # 2:1 R:R
            
            # Simulate trade
            for j in range(i+1, min(i+500, len(data))):
                if data['low'].iloc[j] <= sl:
                    trades.append({"result": "LOSS", "r": -1})
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({"result": "WIN", "r": 2})
                    break
            else:
                # Timeout after 500 bars (about 2 days)
                exit_price = data['close'].iloc[min(i+500, len(data)-1)]
                r = (exit_price - entry) / (entry - sl)
                trades.append({"result": "TIMEOUT", "r": r})
        
        elif strong_downtrend and data['rsi'].iloc[i] > 60:
            # Rally in downtrend
            entry = data['close'].iloc[i]
            sl = entry + (data['atr'].iloc[i] * 1.5)
            tp = entry - (data['atr'].iloc[i] * 3.0)
            
            for j in range(i+1, min(i+500, len(data))):
                if data['high'].iloc[j] >= sl:
                    trades.append({"result": "LOSS", "r": -1})
                    break
                elif data['low'].iloc[j] <= tp:
                    trades.append({"result": "WIN", "r": 2})
                    break
            else:
                exit_price = data['close'].iloc[min(i+500, len(data)-1)]
                r = (entry - exit_price) / (sl - entry)
                trades.append({"result": "TIMEOUT", "r": r})
    
    # Calculate statistics
    print(f"\nGenerated {len(trades)} trades")
    
    if trades:
        wins = sum(1 for t in trades if t["r"] > 0)
        losses = sum(1 for t in trades if t["r"] < 0)
        timeouts = sum(1 for t in trades if t["result"] == "TIMEOUT")
        
        gross_profit = sum(t["r"] for t in trades if t["r"] > 0)
        gross_loss = abs(sum(t["r"] for t in trades if t["r"] < 0))
        
        r_values = [t["r"] for t in trades]
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        stats = {
            "total_trades": len(trades),
            "wins": wins,
            "losses": losses,
            "timeouts": timeouts,
            "win_rate": wins / len(trades),
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float('inf'),
            "expectancy": np.mean(r_values),
            "total_r": sum(r_values),
            "max_drawdown": max_drawdown,
            "avg_win": np.mean([t["r"] for t in trades if t["r"] > 0]) if wins > 0 else 0,
            "avg_loss": np.mean([t["r"] for t in trades if t["r"] < 0]) if losses > 0 else 0
        }
        
        # Print results
        print("\n" + "="*60)
        print("  USDJPYm TREND STRATEGY RESULTS")
        print("="*60)
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
        
        # Assessment
        print("\n  ASSESSMENT:")
        if stats["total_trades"] >= 30:
            if stats["profit_factor"] > 1.3 and stats["expectancy"] > 0.2:
                print("  ? STRATEGY SHOWS PROMISE!")
                print("  Consider forward testing")
            elif stats["profit_factor"] > 1.0:
                print("  ? Strategy is marginal")
                print("  Needs refinement")
            else:
                print("  ? Strategy is not profitable")
                print("  Consider different approach")
        else:
            print("  ? Insufficient trades")
            print(f"    Need 30+, got {stats['total_trades']}")
        
        return stats
    
    return None

if __name__ == "__main__":
    results = run_usdjpy_strategy()
