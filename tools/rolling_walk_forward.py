"""ROLLING WALK-FORWARD VALIDATION - The Gold Standard."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

class RollingWalkForward:
    """Validates strategy using rolling train/test windows."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        self.train_years = 3
        self.test_years = 1
        
    def load_data(self):
        """Load historical data."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        data.set_index('timestamp', inplace=True)
        
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
        df['hour'] = df.index.hour
        
        df['bullish_fvg'] = (df['high'].shift(2) < df['low'])
        
        return df
    
    def run_strategy(self, data, rr_ratio=2.0, sl_atr_mult=2.0):
        """Run strategy with parameters."""
        trades = []
        
        for i in range(200, len(data)):
            # FVG + bias + session
            if not data['bullish_fvg'].iloc[i]:
                continue
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            hour = data['hour'].iloc[i]
            if not ((0 <= hour < 7) or (7 <= hour < 11) or (17 <= hour < 21)):
                continue
            
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * sl_atr_mult)
            tp = entry + (data['atr'].iloc[i] * sl_atr_mult * rr_ratio)
            
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({"r": -1, "date": data.index[i]})
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({"r": rr_ratio, "date": data.index[i]})
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({"r": r, "date": data.index[i]})
        
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
    
    def optimize_on_train(self, train_data):
        """Select optimal parameters on training data ONLY."""
        # Test different R:R ratios on training data
        best_rr = 2.0
        best_expectancy = -float('inf')
        
        for rr in [1.5, 2.0, 2.5]:
            trades = self.run_strategy(train_data, rr_ratio=rr)
            stats = self.calculate_stats(trades)
            
            if stats["trades"] >= 20 and stats["expectancy"] > best_expectancy:
                best_expectancy = stats["expectancy"]
                best_rr = rr
        
        return {"rr_ratio": best_rr}
    
    def run_rolling_walk_forward(self):
        """Run complete rolling walk-forward validation."""
        print("="*70)
        print("  ROLLING WALK-FORWARD VALIDATION")
        print("  Train on past, test on future, roll forward")
        print("="*70)
        
        data = self.load_data()
        if data is None:
            return None
        
        data = self.calculate_indicators(data)
        
        years = sorted(set(data.index.year))
        print(f"\n  Years available: {years}")
        
        # Create rolling windows
        windows = []
        for i in range(len(years) - self.train_years - self.test_years + 1):
            train_years = years[i:i+self.train_years]
            test_year = years[i+self.train_years]
            windows.append((train_years, test_year))
        
        print(f"\n  Rolling windows: {len(windows)}")
        print(f"\n{'='*70}")
        print("  WALK-FORWARD RESULTS")
        print("="*70)
        
        print(f"\n  {'Window':>20s} {'Train':>20s} {'Test':>6s} {'Trades':>7s} {'WinRate':>8s} {'PF':>8s} {'Expect':>8s} {'TotalR':>8s}")
        print(f"  " + "-"*90)
        
        all_test_trades = []
        window_results = []
        
        for train_years, test_year in windows:
            # Split data
            train_start = f"{train_years[0]}-01-01"
            train_end = f"{train_years[-1]}-12-31"
            test_start = f"{test_year}-01-01"
            test_end = f"{test_year}-12-31"
            
            train_data = data[(data.index >= train_start) & (data.index <= train_end)]
            test_data = data[(data.index >= test_start) & (data.index <= test_end)]
            
            # Optimize on TRAIN only
            params = self.optimize_on_train(train_data)
            
            # Test on UNSEEN data
            test_trades = self.run_strategy(test_data, rr_ratio=params["rr_ratio"])
            test_stats = self.calculate_stats(test_trades)
            
            # Collect all test trades
            all_test_trades.extend(test_trades)
            
            window_results.append({
                "train": f"{train_years[0]}-{train_years[-1]}",
                "test": test_year,
                "params": params,
                "stats": test_stats
            })
            
            print(f"  {'Train '+str(train_years[0])+'-'+str(train_years[-1]):>20s} {'? Test '+str(test_year):>20s} {test_stats['trades']:6d} {test_stats['win_rate']*100:7.1f}% {test_stats['pf']:8.3f} {test_stats['expectancy']:+8.3f}R {test_stats['total_r']:+8.1f}R")
        
        # Summary
        print(f"\n{'='*70}")
        print("  WALK-FORWARD SUMMARY")
        print("="*70)
        
        test_expectancies = [w["stats"]["expectancy"] for w in window_results if w["stats"]["trades"] > 0]
        test_pfs = [w["stats"]["pf"] for w in window_results if w["stats"]["trades"] > 0]
        
        if test_expectancies:
            profitable_windows = sum(1 for e in test_expectancies if e > 0)
            total_windows = len(test_expectancies)
            
            print(f"\n  Windows with trades: {total_windows}")
            print(f"  Profitable windows: {profitable_windows}/{total_windows} ({profitable_windows/total_windows*100:.0f}%)")
            print(f"  Mean expectancy: {np.mean(test_expectancies):.3f}R")
            print(f"  Median expectancy: {np.median(test_expectancies):.3f}R")
            print(f"  Std expectancy: {np.std(test_expectancies):.3f}R")
            print(f"  Min expectancy: {np.min(test_expectancies):.3f}R")
            print(f"  Max expectancy: {np.max(test_expectancies):.3f}R")
            print(f"  Mean PF: {np.mean(test_pfs):.3f}")
            
            # Combined OOS performance
            combined_stats = self.calculate_stats(all_test_trades)
            print(f"\n  COMBINED OUT-OF-SAMPLE:")
            print(f"    Trades: {combined_stats['trades']}")
            print(f"    Win rate: {combined_stats['win_rate']*100:.1f}%")
            print(f"    PF: {combined_stats['pf']:.3f}")
            print(f"    Expectancy: {combined_stats['expectancy']:.3f}R")
            print(f"    Total R: {combined_stats['total_r']:.1f}")
            
            # Statistical test on OOS
            r_values = [t["r"] for t in all_test_trades]
            t_stat, p_value = scipy_stats.ttest_1samp(r_values, 0)
            print(f"    P-value: {p_value:.4f}")
            print(f"    Significant: {'YES' if p_value < 0.05 else 'NO'}")
        
        # Final verdict
        print(f"\n{'='*70}")
        print("  FINAL VERDICT")
        print("="*70)
        
        if test_expectancies:
            if (np.mean(test_expectancies) > 0.15 and 
                profitable_windows / total_windows >= 0.6 and 
                np.mean(test_pfs) > 1.2):
                print(f"\n  ? WALK-FORWARD VALIDATION PASSED")
                print(f"  Strategy shows consistent out-of-sample edge")
            elif np.mean(test_expectancies) > 0:
                print(f"\n  ? WALK-FORWARD MARGINAL")
                print(f"  Edge exists but not consistent enough")
            else:
                print(f"\n  ? WALK-FORWARD FAILED")
                print(f"  No out-of-sample edge")
        
        return window_results

if __name__ == "__main__":
    validator = RollingWalkForward()
    results = validator.run_rolling_walk_forward()
