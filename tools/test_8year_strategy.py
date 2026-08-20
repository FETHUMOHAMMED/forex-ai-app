"""Test USDJPY H4 strategy on 8 years of data."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats

def test_8year_strategy():
    """Run strategy on full 8-year dataset."""
    print("="*60)
    print("  USDJPY H4 STRATEGY - 8 YEAR VALIDATION")
    print("="*60)
    
    if not mt5.initialize():
        print("MT5 initialization failed")
        return None
    
    # Download full history
    print("\nDownloading full 8-year history...")
    rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
    
    if rates is None or len(rates) == 0:
        print("Failed to get data")
        mt5.shutdown()
        return None
    
    data = pd.DataFrame(rates)
    data['timestamp'] = pd.to_datetime(data['time'], unit='s')
    
    print(f"Downloaded {len(data)} bars")
    print(f"Range: {data['timestamp'].min()} to {data['timestamp'].max()}")
    
    # Calculate indicators
    print("\nCalculating indicators...")
    data['ema_20'] = data['close'].ewm(span=20, min_periods=20).mean()
    data['ema_50'] = data['close'].ewm(span=50, min_periods=50).mean()
    data['ema_200'] = data['close'].ewm(span=200, min_periods=200).mean()
    
    # ATR
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(window=14, min_periods=1).mean()
    
    # RSI
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # Generate signals
    print("Generating signals...")
    trades = []
    
    for i in range(200, len(data)):
        # Long conditions
        long_condition = (
            data['ema_20'].iloc[i] > data['ema_50'].iloc[i] > data['ema_200'].iloc[i] and
            data['close'].iloc[i] > data['ema_20'].iloc[i] and
            data['rsi'].iloc[i] < 50 and
            data['close'].iloc[i] > data['close'].iloc[i-1]
        )
        
        # Short conditions
        short_condition = (
            data['ema_20'].iloc[i] < data['ema_50'].iloc[i] < data['ema_200'].iloc[i] and
            data['close'].iloc[i] < data['ema_20'].iloc[i] and
            data['rsi'].iloc[i] > 50 and
            data['close'].iloc[i] < data['close'].iloc[i-1]
        )
        
        if long_condition:
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * 2)
            tp = entry + (data['atr'].iloc[i] * 4)
            
            exit_idx = min(i + 20, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({
                        "r": -1, "result": "SL",
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month
                    })
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({
                        "r": 2, "result": "TP",
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month
                    })
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({
                    "r": r, "result": "TIMEOUT",
                    "year": data['timestamp'].iloc[i].year,
                    "month": data['timestamp'].iloc[i].month
                })
        
        elif short_condition:
            entry = data['close'].iloc[i]
            sl = entry + (data['atr'].iloc[i] * 2)
            tp = entry - (data['atr'].iloc[i] * 4)
            
            exit_idx = min(i + 20, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['high'].iloc[j] >= sl:
                    trades.append({
                        "r": -1, "result": "SL",
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month
                    })
                    break
                elif data['low'].iloc[j] <= tp:
                    trades.append({
                        "r": 2, "result": "TP",
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month
                    })
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (entry - exit_price) / (sl - entry)
                trades.append({
                    "r": r, "result": "TIMEOUT",
                    "year": data['timestamp'].iloc[i].year,
                    "month": data['timestamp'].iloc[i].month
                })
    
    mt5.shutdown()
    
    # Results
    if trades:
        trades_df = pd.DataFrame(trades)
        
        wins = (trades_df['r'] > 0).sum()
        total = len(trades_df)
        win_rate = wins / total * 100
        
        gross_profit = trades_df[trades_df['r'] > 0]['r'].sum()
        gross_loss = abs(trades_df[trades_df['r'] < 0]['r'].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        expectancy = trades_df['r'].mean()
        
        print(f"\n{'='*60}")
        print("  8-YEAR BACKTEST RESULTS")
        print(f"{'='*60}")
        print(f"  Total trades: {total}")
        print(f"  Win rate: {win_rate:.1f}%")
        print(f"  Profit factor: {pf:.3f}")
        print(f"  Expectancy: {expectancy:.3f}R")
        print(f"  Total R: {trades_df['r'].sum():.1f}")
        
        # Yearly performance
        print(f"\n  Yearly Performance:")
        yearly = trades_df.groupby('year').agg({
            'r': ['sum', 'count', 'mean']
        })
        for year, row in yearly.iterrows():
            status = "?" if row['r']['sum'] > 0 else "?"
            print(f"    {year}: {row['r']['sum']:.1f}R in {row['r']['count']} trades ({status})")
        
        # Statistical significance
        t_stat, p_value = stats.ttest_1samp(trades_df['r'], 0)
        
        print(f"\n  Statistical Test:")
        print(f"    T-statistic: {t_stat:.3f}")
        print(f"    P-value: {p_value:.3f}")
        print(f"    Significant at 95%: {'YES' if p_value < 0.05 else 'NO'}")
        print(f"    Significant at 90%: {'YES' if p_value < 0.10 else 'NO'}")
        
        # Drawdown analysis
        cumulative = trades_df['r'].cumsum()
        running_max = cumulative.cummax()
        drawdown = cumulative - running_max
        max_dd = drawdown.min()
        
        print(f"\n  Risk Metrics:")
        print(f"    Max drawdown: {max_dd:.1f}R")
        print(f"    Final equity: {cumulative.iloc[-1]:.1f}R")
        
        # Out-of-sample test (last 20% of trades)
        split_idx = int(len(trades_df) * 0.8)
        in_sample = trades_df.iloc[:split_idx]
        out_sample = trades_df.iloc[split_idx:]
        
        print(f"\n  Out-of-Sample Test (last 20%):")
        print(f"    In-sample trades: {len(in_sample)}")
        print(f"    Out-sample trades: {len(out_sample)}")
        if len(out_sample) > 0:
            oos_pf = out_sample[out_sample['r'] > 0]['r'].sum() / abs(out_sample[out_sample['r'] < 0]['r'].sum()) if out_sample[out_sample['r'] < 0]['r'].sum() != 0 else float('inf')
            print(f"    Out-sample PF: {oos_pf:.3f}")
            print(f"    Out-sample expectancy: {out_sample['r'].mean():.3f}R")
        
        return trades_df
    
    return None

if __name__ == "__main__":
    trades = test_8year_strategy()
