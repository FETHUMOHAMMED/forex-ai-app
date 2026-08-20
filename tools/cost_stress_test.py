"""STRESS TEST - Can the edge survive extreme costs?"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

def stress_test_costs():
    """Test strategy under various cost scenarios."""
    print("="*60)
    print("  COST STRESS TEST")
    print("  Testing edge under extreme conditions")
    print("="*60)
    
    # Load data
    if not mt5.initialize():
        return None
    
    rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
    mt5.shutdown()
    
    if rates is None:
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
    
    # Test scenarios
    scenarios = [
        {"name": "No Costs", "spread": 0, "slippage": 0, "commission": 0},
        {"name": "Typical", "spread": 1.2, "slippage": 0.8, "commission": 0.35},
        {"name": "High Costs", "spread": 2.0, "slippage": 2.0, "commission": 0.70},
        {"name": "Very High", "spread": 3.0, "slippage": 3.0, "commission": 1.00},
        {"name": "Extreme", "spread": 5.0, "slippage": 5.0, "commission": 1.50},
        {"name": "ID 163 Event", "spread": 2.0, "slippage": 41.9, "commission": 0.70},
    ]
    
    results = []
    
    for scenario in scenarios:
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
                    spread_cost = scenario["spread"] * 0.001
                    slip_cost = scenario["slippage"] * 0.001
                    
                    entry_actual = entry + spread_cost + slip_cost
                    sl_actual = sl + slip_cost
                    tp_actual = tp - spread_cost
                    
                    # Simulate
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['low'].iloc[j] <= sl_actual:
                            trades.append({"r": -1 - (scenario["commission"] / 10)})
                            break
                        elif data['high'].iloc[j] >= tp_actual:
                            trades.append({"r": 2.5 - (scenario["commission"] / 10)})
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (exit_price - entry_actual) / (entry_actual - sl_actual)
                        trades.append({"r": r - (scenario["commission"] / 10)})
                
                elif not bullish_bias and data['low'].iloc[i-2] > data['high'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry + (data['atr'].iloc[i] * 2.0)
                    tp = entry - (data['atr'].iloc[i] * 5.0)
                    
                    spread_cost = scenario["spread"] * 0.001
                    slip_cost = scenario["slippage"] * 0.001
                    
                    entry_actual = entry - spread_cost - slip_cost
                    sl_actual = sl - slip_cost
                    tp_actual = tp + spread_cost
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['high'].iloc[j] >= sl_actual:
                            trades.append({"r": -1 - (scenario["commission"] / 10)})
                            break
                        elif data['low'].iloc[j] <= tp_actual:
                            trades.append({"r": 2.5 - (scenario["commission"] / 10)})
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (entry_actual - exit_price) / (sl_actual - entry_actual)
                        trades.append({"r": r - (scenario["commission"] / 10)})
        
        if trades:
            r_values = [t["r"] for t in trades]
            wins = sum(1 for r in r_values if r > 0)
            gross_profit = sum(r for r in r_values if r > 0)
            gross_loss = abs(sum(r for r in r_values if r < 0))
            
            results.append({
                "scenario": scenario["name"],
                "trades": len(r_values),
                "win_rate": wins / len(r_values),
                "pf": gross_profit / gross_loss if gross_loss > 0 else float('inf'),
                "expectancy": np.mean(r_values),
                "total_r": sum(r_values)
            })
    
    # Print results
    print(f"\n{'='*60}")
    print("  STRESS TEST RESULTS")
    print("="*60)
    
    for result in results:
        print(f"\n{result['scenario']}:")
        print(f"  Trades: {result['trades']}")
        print(f"  Win rate: {result['win_rate']*100:.1f}%")
        print(f"  PF: {result['pf']:.3f}")
        print(f"  Expectancy: {result['expectancy']:.3f}R")
        print(f"  Total R: {result['total_r']:.1f}")
        
        if result['expectancy'] > 0:
            print(f"  Status: ? PROFITABLE")
        else:
            print(f"  Status: ? UNPROFITABLE")
    
    return results

if __name__ == "__main__":
    results = stress_test_costs()
