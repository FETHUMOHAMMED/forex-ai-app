"""Test if long-only strategy performs better."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def test_long_only():
    """Compare long-only vs long+short."""
    print("="*60)
    print("  LONG-ONLY VS LONG+SHORT COMPARISON")
    print("="*60)
    
    if not mt5.initialize():
        return None
    
    rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
    mt5.shutdown()
    
    data = pd.DataFrame(rates)
    data['timestamp'] = pd.to_datetime(data['time'], unit='s')
    
    # Calculate indicators
    data['ema_50'] = data['close'].ewm(span=50).mean()
    data['ema_200'] = data['close'].ewm(span=200).mean()
    
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(14).mean()
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    
    # Run both strategies
    all_trades = []
    long_trades = []
    
    for i in range(200, len(data)):
        if not (7 <= data['hour'].iloc[i] <= 11):
            continue
        
        bullish_bias = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
        
        if i >= 2:
            if bullish_bias and data['high'].iloc[i-2] < data['low'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * 2.0)
                tp = entry + (data['atr'].iloc[i] * 5.0)
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        long_trades.append({"r": -1})
                        all_trades.append({"r": -1})
                        break
                    elif data['high'].iloc[j] >= tp:
                        long_trades.append({"r": 2.5})
                        all_trades.append({"r": 2.5})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    long_trades.append({"r": r})
                    all_trades.append({"r": r})
            
            elif not bullish_bias and data['low'].iloc[i-2] > data['high'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry + (data['atr'].iloc[i] * 2.0)
                tp = entry - (data['atr'].iloc[i] * 5.0)
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['high'].iloc[j] >= sl:
                        all_trades.append({"r": -1})
                        break
                    elif data['low'].iloc[j] <= tp:
                        all_trades.append({"r": 2.5})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (entry - exit_price) / (sl - entry)
                    all_trades.append({"r": r})
    
    # Compare
    def calc_stats(trades):
        if not trades:
            return {"trades": 0, "win_rate": 0, "pf": 0, "expectancy": 0}
        r_values = [t["r"] for t in trades]
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
    
    long_stats = calc_stats(long_trades)
    all_stats = calc_stats(all_trades)
    
    print(f"\nLONG+SHORT Strategy:")
    print(f"  Trades: {all_stats['trades']}")
    print(f"  Win rate: {all_stats['win_rate']*100:.1f}%")
    print(f"  PF: {all_stats['pf']:.3f}")
    print(f"  Expectancy: {all_stats['expectancy']:.3f}R")
    print(f"  Total R: {all_stats['total_r']:.1f}")
    
    print(f"\nLONG-ONLY Strategy:")
    print(f"  Trades: {long_stats['trades']}")
    print(f"  Win rate: {long_stats['win_rate']*100:.1f}%")
    print(f"  PF: {long_stats['pf']:.3f}")
    print(f"  Expectancy: {long_stats['expectancy']:.3f}R")
    print(f"  Total R: {long_stats['total_r']:.1f}")
    
    print(f"\nIMPROVEMENT:")
    improvement = long_stats['expectancy'] - all_stats['expectancy']
    print(f"  Expectancy improvement: {improvement:.3f}R")
    if improvement > 0:
        print(f"  Long-only is BETTER")
    else:
        print(f"  Keep long+short")
    
    return {"long": long_stats, "all": all_stats}

if __name__ == "__main__":
    results = test_long_only()
