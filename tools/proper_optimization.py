"""PROPER OPTIMIZATION - Target the right metrics."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

class ProperOptimizer:
    """Optimizes for expectancy and stability, NOT win rate."""
    
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
        
        df['bullish_fvg'] = (df['high'].shift(2) < df['low'])
        
        return df
    
    def run_strategy(self, data, tp_rr=2.5, sl_atr_mult=2.0):
        """Run strategy with given R:R parameters."""
        trades = []
        
        for i in range(200, len(data)):
            # FVG + bias + session filter
            if not data['bullish_fvg'].iloc[i]:
                continue
            
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            hour = data['hour'].iloc[i]
            if not ((0 <= hour < 7) or (7 <= hour < 11) or (17 <= hour < 21)):
                continue
            
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * sl_atr_mult)
            tp = entry + (data['atr'].iloc[i] * sl_atr_mult * tp_rr)
            
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({"r": -1})
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({"r": tp_rr})
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({"r": r})
        
        return trades
    
    def calculate_comprehensive_stats(self, trades):
        """Calculate comprehensive statistics."""
        if not trades:
            return None
        
        r_values = [t["r"] for t in trades]
        
        # Basic
        wins = sum(1 for r in r_values if r > 0)
        win_rate = wins / len(r_values)
        gross_profit = sum(r for r in r_values if r > 0)
        gross_loss = abs(sum(r for r in r_values if r < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        expectancy = np.mean(r_values)
        
        # Risk metrics
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_dd = np.min(drawdown)
        
        # Stability (consistency)
        # Split into chunks and check consistency
        chunk_size = max(10, len(r_values) // 10)
        chunks = [r_values[i:i+chunk_size] for i in range(0, len(r_values), chunk_size)]
        chunk_expectancies = [np.mean(chunk) for chunk in chunks if len(chunk) >= 5]
        
        if chunk_expectancies:
            positive_chunks = sum(1 for e in chunk_expectancies if e > 0)
            stability = positive_chunks / len(chunk_expectancies)
        else:
            stability = 0
        
        # Statistical significance
        t_stat, p_value = scipy_stats.ttest_1samp(r_values, 0)
        
        return {
            "trades": len(r_values),
            "win_rate": win_rate,
            "pf": pf,
            "expectancy": expectancy,
            "max_dd": max_dd,
            "stability": stability,
            "p_value": p_value,
            "total_r": sum(r_values)
        }
    
    def optimize_for_expectancy(self, data):
        """Optimize for expectancy (NOT win rate)."""
        print("="*70)
        print("  OPTIMIZATION TARGETING EXPECTANCY")
        print("  NOT win rate - the RIGHT metric")
        print("="*70)
        
        # Test different R:R ratios
        rr_ratios = [1.5, 2.0, 2.5, 3.0, 3.5]
        
        print(f"\n{'='*70}")
        print("  R:R RATIO OPTIMIZATION")
        print("="*70)
        print(f"\n  {'R:R':>5s} {'Trades':>7s} {'WinRate':>8s} {'PF':>8s} {'Expect':>8s} {'MaxDD':>8s} {'Stability':>10s} {'TotalR':>8s}")
        print(f"  " + "-"*70)
        
        results = []
        
        for rr in rr_ratios:
            trades = self.run_strategy(data, tp_rr=rr)
            stats = self.calculate_comprehensive_stats(trades)
            
            if stats:
                results.append({"rr": rr, **stats})
                print(f"  {rr:5.1f} {stats['trades']:7d} {stats['win_rate']*100:7.1f}% {stats['pf']:8.3f} {stats['expectancy']:+8.3f}R {stats['max_dd']:+8.1f}R {stats['stability']*100:9.0f}% {stats['total_r']:+8.1f}R")
        
        # Find best by expectancy (NOT win rate)
        if results:
            best_by_expectancy = max(results, key=lambda x: x["expectancy"])
            best_by_winrate = max(results, key=lambda x: x["win_rate"])
            best_by_pf = max(results, key=lambda x: x["pf"])
            
            print(f"\n{'='*70}")
            print("  OPTIMIZATION RESULTS")
            print("="*70)
            
            print(f"\n  Best by EXPECTANCY (what matters):")
            print(f"    R:R: {best_by_expectancy['rr']}")
            print(f"    Expectancy: {best_by_expectancy['expectancy']:.3f}R")
            print(f"    Win rate: {best_by_expectancy['win_rate']*100:.1f}%")
            print(f"    PF: {best_by_expectancy['pf']:.3f}")
            print(f"    Stability: {best_by_expectancy['stability']*100:.0f}%")
            
            print(f"\n  Best by WIN RATE (vanity metric):")
            print(f"    R:R: {best_by_winrate['rr']}")
            print(f"    Win rate: {best_by_winrate['win_rate']*100:.1f}%")
            print(f"    Expectancy: {best_by_winrate['expectancy']:.3f}R")
            print(f"    PF: {best_by_winrate['pf']:.3f}")
            print(f"    Note: Higher win rate but LOWER expectancy!")
            
            print(f"\n  Best by PROFIT FACTOR (what matters):")
            print(f"    R:R: {best_by_pf['rr']}")
            print(f"    PF: {best_by_pf['pf']:.3f}")
            print(f"    Expectancy: {best_by_pf['expectancy']:.3f}R")
            print(f"    Win rate: {best_by_pf['win_rate']*100:.1f}%")
        
        return results
    
    def demonstrate_win_rate_fallacy(self):
        """Demonstrate why win rate is misleading."""
        print(f"\n{'='*70}")
        print("  WHY WIN RATE IS MISLEADING")
        print("="*70)
        
        examples = [
            {"name": "Strategy A", "win_rate": 0.70, "avg_win": 0.5, "avg_loss": 2.0,
             "expectancy": 0.70 * 0.5 - 0.30 * 2.0},
            {"name": "Strategy B", "win_rate": 0.45, "avg_win": 2.5, "avg_loss": 1.0,
             "expectancy": 0.45 * 2.5 - 0.55 * 1.0},
            {"name": "Strategy C", "win_rate": 0.30, "avg_win": 5.0, "avg_loss": 1.0,
             "expectancy": 0.30 * 5.0 - 0.70 * 1.0},
        ]
        
        print(f"\n  {'Strategy':15s} {'WinRate':>8s} {'AvgWin':>8s} {'AvgLoss':>8s} {'Expectancy':>10s} {'Verdict':>10s}")
        print(f"  " + "-"*65)
        
        for ex in examples:
            verdict = "? GOOD" if ex["expectancy"] > 0 else "? BAD"
            print(f"  {ex['name']:15s} {ex['win_rate']*100:7.1f}% {ex['avg_win']:+7.1f}R {ex['avg_loss']:+7.1f}R {ex['expectancy']:+9.2f}R  {verdict:>10s}")
        
        print(f"\n  KEY INSIGHT:")
        print(f"  Strategy A: 70% win rate but LOSES money (-0.25R)")
        print(f"  Strategy C: 30% win rate but MAKES money (+0.80R)")
        print(f"  Win rate alone is USELESS for evaluating a strategy.")
    
    def run_full_optimization(self):
        """Run complete optimization."""
        data = self.load_data()
        if data is None:
            return None
        
        data = self.calculate_indicators(data)
        
        # Demonstrate win rate fallacy
        self.demonstrate_win_rate_fallacy()
        
        # Optimize for the right metrics
        results = self.optimize_for_expectancy(data)
        
        return results

if __name__ == "__main__":
    optimizer = ProperOptimizer()
    results = optimizer.run_full_optimization()
