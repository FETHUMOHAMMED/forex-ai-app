"""REPLAY WITH REALISTIC ENTRY TIMING - Entry at NEXT bar."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def replay_with_next_bar_entry():
    """Replay V4 with entry at NEXT bar (realistic timing)."""
    print("="*70)
    print("  REPLAY: REALISTIC ENTRY TIMING")
    print("  Signal at bar i ? Entry at bar i+1")
    print("="*70)
    
    if not mt5.initialize():
        return None
    
    rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
    mt5.shutdown()
    
    if rates is None or len(rates) < 200:
        return {"error": "INSUFFICIENT_DATA"}
    
    data = pd.DataFrame(rates)
    data['timestamp'] = pd.to_datetime(data['time'], unit='s')
    
    # Indicators
    data['ema_50'] = data['close'].ewm(span=50).mean()
    data['ema_200'] = data['close'].ewm(span=200).mean()
    
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr'] = tr.rolling(14).mean()
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    
    # Run with BOTH entry timings for comparison
    trades_same_bar = []
    trades_next_bar_open = []
    trades_next_bar_close = []
    
    for i in range(200, len(data) - 1):  # -1 because we need bar i+1
        bullish_fvg = data['high'].iloc[i-2] < data['low'].iloc[i] if i >= 2 else False
        bullish_bias = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
        london = 7 <= data['hour'].iloc[i] < 11
        
        if bullish_fvg and bullish_bias and london:
            # Entry Method 1: Same bar close (optimistic)
            entry_same = data['close'].iloc[i]
            sl_same = entry_same - (data['atr'].iloc[i] * 2.0)
            tp_same = entry_same + (data['atr'].iloc[i] * 4.0)
            
            # Entry Method 2: Next bar OPEN (realistic)
            entry_open = data['open'].iloc[i+1]
            sl_open = entry_open - (data['atr'].iloc[i] * 2.0)
            tp_open = entry_open + (data['atr'].iloc[i] * 4.0)
            
            # Entry Method 3: Next bar CLOSE (conservative)
            entry_next_close = data['close'].iloc[i+1]
            sl_next_close = entry_next_close - (data['atr'].iloc[i] * 2.0)
            tp_next_close = entry_next_close + (data['atr'].iloc[i] * 4.0)
            
            exit_idx = min(i + 50, len(data) - 1)
            
            # Simulate each method
            for entry, sl, tp, trade_list in [
                (entry_same, sl_same, tp_same, trades_same_bar),
                (entry_open, sl_open, tp_open, trades_next_bar_open),
                (entry_next_close, sl_next_close, tp_next_close, trades_next_bar_close)
            ]:
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        trade_list.append({"r": -1})
                        break
                    elif data['high'].iloc[j] >= tp:
                        trade_list.append({"r": 2.0})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    trade_list.append({"r": r})
    
    # Compare results
    def calc(trades):
        if not trades:
            return {"trades": 0}
        r_values = [t["r"] for t in trades]
        wins = sum(1 for r in r_values if r > 0)
        gross_p = sum(r for r in r_values if r > 0)
        gross_l = abs(sum(r for r in r_values if r < 0))
        return {
            "trades": len(r_values),
            "win_rate": wins / len(r_values),
            "pf": gross_p / gross_l if gross_l > 0 else float('inf'),
            "expectancy": np.mean(r_values)
        }
    
    same = calc(trades_same_bar)
    next_open = calc(trades_next_bar_open)
    next_close = calc(trades_next_bar_close)
    
    print(f"\n  {'Method':25s} {'Trades':>7s} {'WinRate':>8s} {'PF':>8s} {'Expect':>8s}")
    print(f"  " + "-"*60)
    print(f"  {'Same bar close':25s} {same['trades']:7d} {same['win_rate']*100:7.1f}% {same['pf']:8.3f} {same['expectancy']:+8.3f}R")
    print(f"  {'Next bar open':25s} {next_open['trades']:7d} {next_open['win_rate']*100:7.1f}% {next_open['pf']:8.3f} {next_open['expectancy']:+8.3f}R")
    print(f"  {'Next bar close':25s} {next_close['trades']:7d} {next_close['win_rate']*100:7.1f}% {next_close['pf']:8.3f} {next_close['expectancy']:+8.3f}R")
    
    print(f"\n  IMPACT OF ENTRY TIMING:")
    impact = same['expectancy'] - next_open['expectancy']
    print(f"  Same-bar overstatement: {impact:+.3f}R")
    print(f"  This is how much the edge is inflated by optimistic entry.")
    
    return {
        "same_bar": same,
        "next_bar_open": next_open,
        "next_bar_close": next_close
    }

if __name__ == "__main__":
    results = replay_with_next_bar_entry()
