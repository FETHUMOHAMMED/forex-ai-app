"""PROGRESSIVE FILTER TEST - Find optimal filter combination."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def test_progressive_filters():
    """Add filters one at a time to find optimal combination."""
    print("="*70)
    print("  PROGRESSIVE FILTER ANALYSIS")
    print("  Finding the right combination")
    print("="*70)
    
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
    
    # FVG
    data['bullish_fvg'] = (data['high'].shift(2) < data['low'])
    
    # Session
    data['good_session'] = (
        ((data['hour'] >= 0) & (data['hour'] < 7)) |
        ((data['hour'] >= 7) & (data['hour'] < 11)) |
        ((data['hour'] >= 17) & (data['hour'] < 21))
    )
    
    # Test progressive combinations
    variants = [
        ("FVG only", ["bullish_fvg"]),
        ("FVG + Bullish Bias", ["bullish_fvg", "bullish_bias"]),
        ("FVG + Bias + Session", ["bullish_fvg", "bullish_bias", "good_session"]),
        ("FVG + Bias + London", ["bullish_fvg", "bullish_bias", "london_only"]),
        ("FVG + Bias + ATR Filter", ["bullish_fvg", "bullish_bias", "atr_filter"]),
        ("FVG + Bias + Session + ATR", ["bullish_fvg", "bullish_bias", "good_session", "atr_filter"]),
    ]
    
    print(f"\n{'='*70}")
    print("  RESULTS")
    print("="*70)
    print(f"\n  {'Variant':30s} {'Trades':>6s} {'WinRate':>8s} {'PF':>8s} {'Expect':>8s} {'TotalR':>8s}")
    print(f"  " + "-"*75)
    
    for name, filters in variants:
        trades = []
        
        for i in range(200, len(data)):
            # Always require FVG
            if "bullish_fvg" in filters and not data['bullish_fvg'].iloc[i]:
                continue
            
            # Bullish bias
            if "bullish_bias" in filters and data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            # Session
            if "good_session" in filters and not data['good_session'].iloc[i]:
                continue
            
            # London only
            if "london_only" in filters:
                if not (7 <= data['hour'].iloc[i] < 11):
                    continue
            
            # ATR filter
            if "atr_filter" in filters:
                atr_ratio = data['atr'].iloc[i] / data['atr'].rolling(50).mean().iloc[i]
                if atr_ratio > 1.5:
                    continue
            
            # Take trade
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * 2.0)
            tp = entry + (data['atr'].iloc[i] * 5.0)
            
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({"r": -1})
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({"r": 2.5})
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({"r": r})
        
        if trades:
            r_values = [t["r"] for t in trades]
            wins = sum(1 for r in r_values if r > 0)
            win_rate = wins / len(r_values)
            gross_profit = sum(r for r in r_values if r > 0)
            gross_loss = abs(sum(r for r in r_values if r < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            expectancy = np.mean(r_values)
            total_r = sum(r_values)
            
            print(f"  {name:30s} {len(trades):6d} {win_rate*100:7.1f}% {pf:8.3f} {expectancy:+8.3f}R {total_r:+8.1f}R")
        else:
            print(f"  {name:30s} {0:6d} {'-':>8s} {'-':>8s} {'-':>8s} {'-':>8s}")
    
    return None

if __name__ == "__main__":
    test_progressive_filters()
