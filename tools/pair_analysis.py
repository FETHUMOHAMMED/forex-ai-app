"""PAIR-LEVEL ANALYSIS - Does the strategy work across all pairs?"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
import json
from pathlib import Path

class PairAnalyzer:
    """Tests strategy across multiple currency pairs."""
    
    def __init__(self):
        self.pairs = ["EURUSDm", "GBPUSDm", "USDJPYm", "AUDUSDm", "USDCADm", "USDCHFm"]
        self.timeframe = mt5.TIMEFRAME_H4
        
    def load_pair_data(self, symbol):
        """Load data for a specific pair."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        if rates is None or len(rates) == 0:
            return None
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        return data
    
    def calculate_indicators(self, data):
        """Calculate indicators."""
        df = data.copy()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        return df
    
    def run_strategy_on_pair(self, data, symbol):
        """Run the long-only FVG strategy on a pair."""
        trades = []
        
        for i in range(200, len(data)):
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            # Long only
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * 2.0)
                tp = entry + (data['atr'].iloc[i] * 5.0)
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        trades.append({
                            "r": -1,
                            "symbol": symbol,
                            "year": data['timestamp'].iloc[i].year
                        })
                        break
                    elif data['high'].iloc[j] >= tp:
                        trades.append({
                            "r": 2.5,
                            "symbol": symbol,
                            "year": data['timestamp'].iloc[i].year
                        })
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    trades.append({
                        "r": r,
                        "symbol": symbol,
                        "year": data['timestamp'].iloc[i].year
                    })
        
        return trades
    
    def calculate_stats(self, trades):
        """Calculate statistics."""
        if not trades:
            return {"trades": 0, "win_rate": 0, "pf": 0, "expectancy": 0, "total_r": 0}
        
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
    
    def run_pair_analysis(self):
        """Run strategy on all pairs."""
        print("="*70)
        print("  PAIR-LEVEL ANALYSIS")
        print("  Testing Strategy Across 6 Currency Pairs")
        print("="*70)
        
        all_results = {}
        all_trades = []
        
        for symbol in self.pairs:
            print(f"\n{'='*70}")
            print(f"  Testing {symbol}")
            print(f"{'='*70}")
            
            data = self.load_pair_data(symbol)
            if data is None:
                print(f"  No data available for {symbol}")
                continue
            
            data = self.calculate_indicators(data)
            trades = self.run_strategy_on_pair(data, symbol)
            
            if not trades:
                print(f"  No trades generated for {symbol}")
                all_results[symbol] = {"trades": 0}
                continue
            
            stats = self.calculate_stats(trades)
            all_results[symbol] = stats
            all_trades.extend(trades)
            
            print(f"\n  {symbol} Results:")
            print(f"    Trades: {stats['trades']}")
            print(f"    Win rate: {stats['win_rate']*100:.1f}%")
            print(f"    Profit factor: {stats['pf']:.3f}")
            print(f"    Expectancy: {stats['expectancy']:.3f}R")
            print(f"    Total R: {stats['total_r']:.1f}")
            
            # Statistical significance
            if stats['trades'] >= 10:
                r_values = [t["r"] for t in trades]
                t_stat, p_value = scipy_stats.ttest_1samp(r_values, 0)
                print(f"    P-value: {p_value:.4f}")
                print(f"    Significant: {'YES' if p_value < 0.05 else 'NO'}")
        
        # Summary comparison
        print(f"\n{'='*70}")
        print("  PAIR COMPARISON SUMMARY")
        print("="*70)
        
        print(f"\n  Pair       Trades  WinRate  PF      Expectancy  Total R")
        print(f"  " + "-"*65)
        
        for symbol, stats in all_results.items():
            if stats["trades"] > 0:
                status = "?" if stats["expectancy"] > 0.2 else "?" if stats["expectancy"] > 0 else "?"
                print(f"  {symbol:10s}  {stats['trades']:3d}    {stats['win_rate']*100:5.1f}%  {stats['pf']:6.3f}  {stats['expectancy']:+.3f}R    {stats['total_r']:+.1f}R  {status}")
            else:
                print(f"  {symbol:10s}    0     -      -         -          -")
        
        # Combined portfolio stats
        if all_trades:
            combined_stats = self.calculate_stats(all_trades)
            print(f"\n  COMBINED (All Pairs):")
            print(f"    Trades: {combined_stats['trades']}")
            print(f"    Win rate: {combined_stats['win_rate']*100:.1f}%")
            print(f"    PF: {combined_stats['pf']:.3f}")
            print(f"    Expectancy: {combined_stats['expectancy']:.3f}R")
            print(f"    Total R: {combined_stats['total_r']:.1f}")
        
        # Key insights
        print(f"\n{'='*70}")
        print("  KEY INSIGHTS")
        print("="*70)
        
        profitable_pairs = [s for s, stats in all_results.items() if stats.get("expectancy", 0) > 0.2]
        marginal_pairs = [s for s, stats in all_results.items() if 0 < stats.get("expectancy", 0) <= 0.2]
        unprofitable_pairs = [s for s, stats in all_results.items() if stats.get("expectancy", 0) <= 0]
        
        print(f"\n  Strong pairs (exp > 0.2R): {len(profitable_pairs)}")
        for pair in profitable_pairs:
            print(f"    ? {pair}")
        
        print(f"\n  Marginal pairs (0 < exp <= 0.2R): {len(marginal_pairs)}")
        for pair in marginal_pairs:
            print(f"    ? {pair}")
        
        print(f"\n  Unprofitable pairs (exp <= 0): {len(unprofitable_pairs)}")
        for pair in unprofitable_pairs:
            print(f"    ? {pair}")
        
        return all_results

if __name__ == "__main__":
    analyzer = PairAnalyzer()
    results = analyzer.run_pair_analysis()
    
    # Save results
    if results:
        results_path = Path("research/pair_analysis_results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {results_path}")
