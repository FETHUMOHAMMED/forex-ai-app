"""Run simple research on available data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timezone

def simple_backtest(data):
    """Run a simple backtest."""
    print(f"Running simple backtest on {len(data)} bars...")
    
    # Calculate basic indicators
    data['ema_20'] = data['close'].ewm(span=20, min_periods=20).mean()
    data['ema_50'] = data['close'].ewm(span=50, min_periods=50).mean()
    data['ema_200'] = data['close'].ewm(span=200, min_periods=200).mean()
    
    # Generate signals
    trades = []
    
    for i in range(200, len(data)):
        # Simple trend following
        if data['ema_20'].iloc[i] > data['ema_50'].iloc[i] > data['ema_200'].iloc[i]:
            # Bullish trend
            if data['close'].iloc[i] > data['ema_20'].iloc[i]:
                # Entry signal
                entry = data['close'].iloc[i]
                sl = entry - (data['atr_14'].iloc[i] * 1.5) if 'atr_14' in data.columns else entry * 0.995
                tp = entry + (entry - sl) * 2
                
                # Simulate trade
                for j in range(i+1, min(i+500, len(data))):
                    if data['low'].iloc[j] <= sl:
                        trades.append({"result": "LOSS", "r": -1})
                        break
                    elif data['high'].iloc[j] >= tp:
                        trades.append({"result": "WIN", "r": 2})
                        break
                else:
                    # Timeout
                    exit_price = data['close'].iloc[min(i+500, len(data)-1)]
                    r = (exit_price - entry) / (entry - sl)
                    trades.append({"result": "TIMEOUT", "r": r})
        
        elif data['ema_20'].iloc[i] < data['ema_50'].iloc[i] < data['ema_200'].iloc[i]:
            # Bearish trend
            if data['close'].iloc[i] < data['ema_20'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry + (data['atr_14'].iloc[i] * 1.5) if 'atr_14' in data.columns else entry * 1.005
                tp = entry - (sl - entry) * 2
                
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
    if trades:
        wins = sum(1 for t in trades if t["r"] > 0)
        losses = sum(1 for t in trades if t["r"] < 0)
        total = len(trades)
        
        gross_profit = sum(t["r"] for t in trades if t["r"] > 0)
        gross_loss = abs(sum(t["r"] for t in trades if t["r"] < 0))
        
        stats = {
            "total_trades": total,
            "win_rate": wins / total,
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float('inf'),
            "expectancy": np.mean([t["r"] for t in trades]),
            "total_r": sum(t["r"] for t in trades),
            "avg_win": np.mean([t["r"] for t in trades if t["r"] > 0]) if wins > 0 else 0,
            "avg_loss": np.mean([t["r"] for t in trades if t["r"] < 0]) if losses > 0 else 0
        }
    else:
        stats = {
            "total_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "expectancy": 0,
            "total_r": 0,
            "avg_win": 0,
            "avg_loss": 0
        }
    
    return stats

def main():
    """Main research function."""
    print("="*60)
    print("  SIMPLE RESEARCH PIPELINE")
    print("="*60)
    
    # Load data
    data_path = Path("data/research/all_historical_data.pkl")
    if not data_path.exists():
        print("No data found. Generating test data...")
        # Import and run data generator
        sys.path.insert(0, str(Path("tools").resolve()))
        from generate_test_data import generate_all_data
        generate_all_data()
    
    print("\nLoading data...")
    with open(data_path, "rb") as f:
        all_data = pickle.load(f)
    
    # Check data structure
    print(f"Data keys: {list(all_data.keys())}")
    
    # Find available timeframes
    if "EURUSD" in all_data:
        print(f"EURUSD timeframes: {list(all_data['EURUSD'].keys())}")
        
        # Use M5 data if available
        if "M5" in all_data["EURUSD"]:
            data = all_data["EURUSD"]["M5"]
        else:
            # Use first available timeframe
            first_tf = list(all_data["EURUSD"].keys())[0]
            data = all_data["EURUSD"][first_tf]
            print(f"Using {first_tf} data")
    else:
        # Try to find any data
        print("No EURUSD data found, looking for other symbols...")
        for symbol in all_data.keys():
            if isinstance(all_data[symbol], dict):
                for tf in all_data[symbol].keys():
                    data = all_data[symbol][tf]
                    print(f"Using {symbol} {tf} data")
                    break
                break
    
    # Calculate ATR
    print("\nCalculating ATR...")
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr_14'] = tr.rolling(window=14, min_periods=1).mean()
    
    # Run backtest
    print("\nRunning backtest...")
    results = simple_backtest(data)
    
    # Print results
    print("\n" + "="*60)
    print("  BACKTEST RESULTS")
    print("="*60)
    for key, value in results.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    # Assessment
    print("\n  ASSESSMENT:")
    if results["total_trades"] >= 30:
        if results["profit_factor"] > 1.3 and results["expectancy"] > 0.2:
            print("  ? Strategy shows promise")
        elif results["profit_factor"] > 1.0:
            print("  ? Strategy is marginal - needs improvement")
        else:
            print("  ? Strategy is not profitable")
    else:
        print("  ? Insufficient trades for assessment")
        print(f"    Need at least 30 trades, got {results['total_trades']}")
    
    print("="*60)

if __name__ == "__main__":
    main()
