"""INVESTIGATE DISCREPANCY - Why is long-only better than aggregate?"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

class DiscrepancyInvestigator:
    """Investigates why long-only USDJPY outperforms aggregate."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
    def load_data(self):
        """Load historical data."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        return data
    
    def investigate_difference(self):
        """Compare long+short vs long-only performance."""
        print("="*70)
        print("  DISCREPANCY INVESTIGATION")
        print("  Why Long-Only Outperforms Aggregate")
        print("="*70)
        
        data = self.load_data()
        if data is None:
            return None
        
        # Calculate indicators
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean()
        
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
        
        # Run BOTH strategies
        long_trades = []
        short_trades = []
        
        for i in range(200, len(data)):
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            # LONG trades (bullish bias)
            if data['ema_50'].iloc[i] > data['ema_200'].iloc[i]:
                if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry - (data['atr'].iloc[i] * 2.0)
                    tp = entry + (data['atr'].iloc[i] * 5.0)
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['low'].iloc[j] <= sl:
                            long_trades.append({"r": -1, "year": data['timestamp'].iloc[i].year})
                            break
                        elif data['high'].iloc[j] >= tp:
                            long_trades.append({"r": 2.5, "year": data['timestamp'].iloc[i].year})
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (exit_price - entry) / (entry - sl)
                        long_trades.append({"r": r, "year": data['timestamp'].iloc[i].year})
            
            # SHORT trades (bearish bias)
            elif data['ema_50'].iloc[i] < data['ema_200'].iloc[i]:
                if i >= 2 and data['low'].iloc[i-2] > data['high'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry + (data['atr'].iloc[i] * 2.0)
                    tp = entry - (data['atr'].iloc[i] * 5.0)
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['high'].iloc[j] >= sl:
                            short_trades.append({"r": -1, "year": data['timestamp'].iloc[i].year})
                            break
                        elif data['low'].iloc[j] <= tp:
                            short_trades.append({"r": 2.5, "year": data['timestamp'].iloc[i].year})
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (entry - exit_price) / (sl - entry)
                        short_trades.append({"r": r, "year": data['timestamp'].iloc[i].year})
        
        # Analyze results
        all_trades = long_trades + short_trades
        
        def calc_stats(trades):
            if not trades:
                return {"trades": 0}
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
        short_stats = calc_stats(short_trades)
        all_stats = calc_stats(all_trades)
        
        # Print comparison
        print(f"\n{'='*70}")
        print("  LONG VS SHORT COMPARISON")
        print("="*70)
        
        print(f"\n  LONG TRADES:")
        print(f"    Trades: {long_stats['trades']}")
        print(f"    Win rate: {long_stats['win_rate']*100:.1f}%")
        print(f"    PF: {long_stats['pf']:.3f}")
        print(f"    Expectancy: {long_stats['expectancy']:.3f}R")
        print(f"    Total R: {long_stats['total_r']:.1f}")
        
        print(f"\n  SHORT TRADES:")
        print(f"    Trades: {short_stats['trades']}")
        print(f"    Win rate: {short_stats['win_rate']*100:.1f}%")
        print(f"    PF: {short_stats['pf']:.3f}")
        print(f"    Expectancy: {short_stats['expectancy']:.3f}R")
        print(f"    Total R: {short_stats['total_r']:.1f}")
        
        print(f"\n  COMBINED:")
        print(f"    Trades: {all_stats['trades']}")
        print(f"    Win rate: {all_stats['win_rate']*100:.1f}%")
        print(f"    PF: {all_stats['pf']:.3f}")
        print(f"    Expectancy: {all_stats['expectancy']:.3f}R")
        print(f"    Total R: {all_stats['total_r']:.1f}")
        
        # Key insight
        print(f"\n{'='*70}")
        print("  KEY INSIGHT")
        print("="*70)
        
        short_drag = short_stats['total_r']
        long_only_total = long_stats['total_r']
        
        print(f"\n  Short trades added: {short_drag:.1f}R")
        print(f"  Long-only total: {long_only_total:.1f}R")
        
        if short_drag < 0:
            print(f"\n  Short trades are DRAGGING DOWN performance by {abs(short_drag):.1f}R")
            print(f"  Removing shorts improves total R by {abs(short_drag):.1f}R")
            print(f"  Long-only is clearly superior")
        
        # Statistical tests
        if long_stats['trades'] >= 10:
            long_r = [t["r"] for t in long_trades]
            t_stat, p_value = scipy_stats.ttest_1samp(long_r, 0)
            print(f"\n  Long-only statistics:")
            print(f"    T-statistic: {t_stat:.3f}")
            print(f"    P-value: {p_value:.4f}")
            print(f"    Significant: {'YES' if p_value < 0.05 else 'NO'}")
        
        if short_stats['trades'] >= 10:
            short_r = [t["r"] for t in short_trades]
            t_stat, p_value = scipy_stats.ttest_1samp(short_r, 0)
            print(f"\n  Short-only statistics:")
            print(f"    T-statistic: {t_stat:.3f}")
            print(f"    P-value: {p_value:.4f}")
            print(f"    Significant: {'YES' if p_value < 0.05 else 'NO'}")
        
        # Yearly breakdown
        print(f"\n{'='*70}")
        print("  YEARLY BREAKDOWN")
        print("="*70)
        
        long_df = pd.DataFrame(long_trades)
        short_df = pd.DataFrame(short_trades)
        
        print(f"\n  Year    Long R    Short R    Combined")
        print(f"  " + "-"*50)
        
        for year in sorted(set([t['year'] for t in all_trades])):
            long_r = long_df[long_df['year'] == year]['r'].sum() if year in long_df['year'].values else 0
            short_r = short_df[short_df['year'] == year]['r'].sum() if year in short_df['year'].values else 0
            combined = long_r + short_r
            
            print(f"  {year}    {long_r:+.1f}     {short_r:+.1f}      {combined:+.1f}")
        
        return {
            "long": long_stats,
            "short": short_stats,
            "combined": all_stats
        }

if __name__ == "__main__":
    investigator = DiscrepancyInvestigator()
    results = investigator.investigate_difference()
