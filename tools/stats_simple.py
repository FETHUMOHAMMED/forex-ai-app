"""COMPREHENSIVE STATISTICS - Simple Version."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run_analysis():
    """Run complete statistics analysis."""
    print("="*70)
    print("  COMPREHENSIVE STRATEGY STATISTICS")
    print("="*70)
    
    # Load data
    if not mt5.initialize():
        print("MT5 init failed")
        return None
    
    rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
    mt5.shutdown()
    
    if rates is None:
        print("No data")
        return None
    
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
    
    # Run strategy
    trades = []
    
    for i in range(200, len(data)):
        if not (7 <= data['hour'].iloc[i] <= 11):
            continue
        
        bullish_bias = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
        
        if i >= 2:
            if bullish_bias and data['high'].iloc[i-2] < data['low'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * 2.0)
                tp = entry + (data['atr'].iloc[i] * 5.0)
                
                # Apply costs
                entry_actual = entry + 0.002  # 2 pips total cost
                sl_actual = sl + 0.0008
                tp_actual = tp - 0.0012
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl_actual:
                        trades.append({
                            "r": -1.035,
                            "result": "SL",
                            "entry_time": data['timestamp'].iloc[i],
                            "exit_time": data['timestamp'].iloc[j],
                            "direction": "BUY",
                            "bars_held": j - i,
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
                        break
                    elif data['high'].iloc[j] >= tp_actual:
                        trades.append({
                            "r": 2.465,
                            "result": "TP",
                            "entry_time": data['timestamp'].iloc[i],
                            "exit_time": data['timestamp'].iloc[j],
                            "direction": "BUY",
                            "bars_held": j - i,
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry_actual) / (entry_actual - sl_actual)
                    trades.append({
                        "r": r - 0.035,
                        "result": "TIMEOUT",
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[exit_idx],
                        "direction": "BUY",
                        "bars_held": 50,
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month
                    })
            
            elif not bullish_bias and data['low'].iloc[i-2] > data['high'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry + (data['atr'].iloc[i] * 2.0)
                tp = entry - (data['atr'].iloc[i] * 5.0)
                
                entry_actual = entry - 0.002
                sl_actual = sl - 0.0008
                tp_actual = tp + 0.0012
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['high'].iloc[j] >= sl_actual:
                        trades.append({
                            "r": -1.035,
                            "result": "SL",
                            "entry_time": data['timestamp'].iloc[i],
                            "exit_time": data['timestamp'].iloc[j],
                            "direction": "SELL",
                            "bars_held": j - i,
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
                        break
                    elif data['low'].iloc[j] <= tp_actual:
                        trades.append({
                            "r": 2.465,
                            "result": "TP",
                            "entry_time": data['timestamp'].iloc[i],
                            "exit_time": data['timestamp'].iloc[j],
                            "direction": "SELL",
                            "bars_held": j - i,
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (entry_actual - exit_price) / (sl_actual - entry_actual)
                    trades.append({
                        "r": r - 0.035,
                        "result": "TIMEOUT",
                        "entry_time": data['timestamp'].iloc[i],
                        "exit_time": data['timestamp'].iloc[exit_idx],
                        "direction": "SELL",
                        "bars_held": 50,
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month
                    })
    
    if not trades:
        print("No trades")
        return None
    
    trades_df = pd.DataFrame(trades)
    r_values = trades_df['r'].values
    
    # Basic stats
    total = len(r_values)
    wins = r_values[r_values > 0]
    losses = r_values[r_values < 0]
    win_rate = len(wins) / total
    loss_rate = len(losses) / total
    avg_win = np.mean(wins) if len(wins) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Expectancy
    expectancy_simple = (win_rate * avg_win) - (loss_rate * abs(avg_loss))
    expectancy_actual = np.mean(r_values)
    
    # Risk metrics
    cumulative = np.cumsum(r_values)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max
    max_dd = np.min(drawdown)
    recovery_factor = cumulative[-1] / abs(max_dd) if max_dd < 0 else float('inf')
    sharpe = np.mean(r_values) / np.std(r_values) if np.std(r_values) > 0 else 0
    
    downside = r_values[r_values < 0]
    downside_dev = np.std(downside) if len(downside) > 0 else 0
    sortino = np.mean(r_values) / downside_dev if downside_dev > 0 else 0
    
    # Consecutive losses
    max_consec = 0
    current = 0
    for r in r_values:
        if r < 0:
            current += 1
            max_consec = max(max_consec, current)
        else:
            current = 0
    
    # Print everything
    print(f"\n1. BASIC STATISTICS")
    print(f"   Total trades: {total}")
    print(f"   Win rate: {win_rate*100:.1f}%")
    print(f"   Loss rate: {loss_rate*100:.1f}%")
    print(f"   Average win: +{avg_win:.2f}R")
    print(f"   Average loss: {avg_loss:.2f}R")
    print(f"   Profit factor: {pf:.3f}")
    
    print(f"\n2. EXPECTANCY ANALYSIS")
    print(f"   Simple formula: ({win_rate*100:.1f}% x {avg_win:.2f}) - ({loss_rate*100:.1f}% x {abs(avg_loss):.2f})")
    print(f"   Simple result: {expectancy_simple:.3f}R")
    print(f"   Actual result: {expectancy_actual:.3f}R")
    
    print(f"\n3. RISK METRICS")
    print(f"   Max drawdown: {max_dd:.1f}R")
    print(f"   Recovery factor: {recovery_factor:.2f}")
    print(f"   Sharpe ratio: {sharpe:.3f}")
    print(f"   Sortino ratio: {sortino:.3f}")
    print(f"   Max consecutive losses: {max_consec}")
    
    print(f"\n4. R-MULTIPLE DISTRIBUTION")
    print(f"   5th percentile: {np.percentile(r_values, 5):.2f}R")
    print(f"   25th percentile: {np.percentile(r_values, 25):.2f}R")
    print(f"   Median: {np.percentile(r_values, 50):.2f}R")
    print(f"   75th percentile: {np.percentile(r_values, 75):.2f}R")
    print(f"   95th percentile: {np.percentile(r_values, 95):.2f}R")
    
    print(f"\n5. HOLDING TIME")
    avg_bars = trades_df['bars_held'].mean()
    print(f"   Average bars held: {avg_bars:.1f}")
    print(f"   Average hours held: {avg_bars * 4:.1f}")
    print(f"   Average days held: {avg_bars * 4 / 24:.1f}")
    
    print(f"\n6. DIRECTION ANALYSIS")
    for direction in ['BUY', 'SELL']:
        dir_trades = trades_df[trades_df['direction'] == direction]
        if len(dir_trades) > 0:
            dir_win_rate = (dir_trades['r'] > 0).mean()
            dir_exp = dir_trades['r'].mean()
            print(f"   {direction}: {len(dir_trades)} trades, {dir_win_rate*100:.1f}% win, {dir_exp:.2f}R exp")
    
    print(f"\n7. MONTHLY PERFORMANCE")
    trades_df['month_key'] = trades_df['year'].astype(str) + '-' + trades_df['month'].astype(str).str.zfill(2)
    monthly = trades_df.groupby('month_key')['r'].agg(['sum', 'count'])
    
    profitable_months = (monthly['sum'] > 0).sum()
    total_months = len(monthly)
    
    print(f"   Profitable months: {profitable_months}/{total_months}")
    print(f"   Best month: {monthly['sum'].max():.1f}R")
    print(f"   Worst month: {monthly['sum'].min():.1f}R")
    
    print(f"\n{'='*70}")
    print("  FINAL ASSESSMENT")
    print("="*70)
    
    checks = [
        (expectancy_actual > 0.2, f"Expectancy > 0.2R: {expectancy_actual:.3f}R"),
        (pf > 1.3, f"Profit factor > 1.3: {pf:.3f}"),
        (sortino > 1.0, f"Sortino > 1.0: {sortino:.3f}"),
        (recovery_factor > 2.0, f"Recovery factor > 2: {recovery_factor:.2f}"),
        (total > 100, f"Sample > 100: {total}"),
        (abs(max_dd) < 15, f"Max DD < 15R: {abs(max_dd):.1f}R"),
    ]
    
    for passed, desc in checks:
        status = "PASS" if passed else "WARN"
        print(f"  [{status}] {desc}")
    
    return trades_df

if __name__ == "__main__":
    trades = run_analysis()
