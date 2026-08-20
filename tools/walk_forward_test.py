"""WALK-FORWARD TESTING - The Gold Standard of Strategy Validation."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from datetime import datetime, timedelta
import json
from pathlib import Path

class WalkForwardTester:
    """Tests strategy across multiple rolling train/test periods."""
    
    def __init__(self):
        self.strategy_name = "FVG_H4_2.5R_London"
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
        # Walk-forward configuration
        self.train_years = 3  # 3 years training
        self.test_years = 1   # 1 year testing
        self.rolling = True   # Rolling window
        
        self.results = []
        
    def load_data(self):
        """Load full historical data."""
        if not mt5.initialize():
            print("MT5 initialization failed")
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        if rates is None:
            return None
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        data.set_index('timestamp', inplace=True)
        
        return data
    
    def calculate_indicators(self, data):
        """Calculate all indicators."""
        df = data.copy()
        
        # EMAs
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        # Session
        df['hour'] = df.index.hour
        
        return df
    
    def run_strategy(self, data, params):
        """Run strategy with given parameters."""
        trades = []
        
        for i in range(200, len(data)):
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            bullish_bias = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
            
            if i >= 2:
                if bullish_bias and data['high'].iloc[i-2] < data['low'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry - (data['atr'].iloc[i] * params['sl_mult'])
                    tp = entry + (data['atr'].iloc[i] * params['sl_mult'] * params['rr'])
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['low'].iloc[j] <= sl:
                            trades.append({"r": -1, "result": "SL"})
                            break
                        elif data['high'].iloc[j] >= tp:
                            trades.append({"r": params['rr'], "result": "TP"})
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (exit_price - entry) / (entry - sl)
                        trades.append({"r": r, "result": "TIMEOUT"})
                
                elif not bullish_bias and data['low'].iloc[i-2] > data['high'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry + (data['atr'].iloc[i] * params['sl_mult'])
                    tp = entry - (data['atr'].iloc[i] * params['sl_mult'] * params['rr'])
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['high'].iloc[j] >= sl:
                            trades.append({"r": -1, "result": "SL"})
                            break
                        elif data['low'].iloc[j] <= tp:
                            trades.append({"r": params['rr'], "result": "TP"})
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (entry - exit_price) / (sl - entry)
                        trades.append({"r": r, "result": "TIMEOUT"})
        
        return trades
    
    def calculate_stats(self, trades):
        """Calculate statistics for trades."""
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
        """Optimize parameters on training data only."""
        train_data = self.calculate_indicators(train_data)
        
        param_variations = [
            {"sl_mult": 1.5, "rr": 2.0},
            {"sl_mult": 2.0, "rr": 2.0},
            {"sl_mult": 1.5, "rr": 2.5},
            {"sl_mult": 2.0, "rr": 2.5},
        ]
        
        best_params = None
        best_score = -float('inf')
        
        for params in param_variations:
            trades = self.run_strategy(train_data, params)
            stats = self.calculate_stats(trades)
            
            if stats["trades"] >= 10:
                # Score based on expectancy and consistency
                score = stats["expectancy"] * np.sqrt(stats["trades"])
                
                if score > best_score:
                    best_score = score
                    best_params = params
        
        return best_params
    
    def run_walk_forward(self):
        """Run complete walk-forward analysis."""
        print("="*60)
        print("  WALK-FORWARD TESTING")
        print("  Rolling Train/Test Validation")
        print("="*60)
        
        # Load data
        data = self.load_data()
        if data is None:
            return None
        
        print(f"\nData: {len(data)} bars")
        print(f"Range: {data.index.min()} to {data.index.max()}")
        
        # Define rolling periods
        years = sorted(set(data.index.year))
        print(f"\nYears available: {years}")
        
        # Create rolling windows
        windows = []
        
        for i in range(len(years) - self.train_years - self.test_years + 1):
            train_start = years[i]
            train_end = years[i + self.train_years - 1]
            test_year = years[i + self.train_years]
            
            windows.append({
                "train_start": str(train_start),
                "train_end": str(train_end),
                "test_year": str(test_year)
            })
        
        print(f"\nWalk-forward windows: {len(windows)}")
        
        # Run each window
        for window in windows:
            print(f"\n{'='*60}")
            print(f"  Window: Train {window['train_start']}-{window['train_end']} ? Test {window['test_year']}")
            print(f"{'='*60}")
            
            # Split data
            train_mask = (data.index >= window['train_start']) & (data.index <= f"{window['train_end']}-12-31")
            test_mask = (data.index >= f"{window['test_year']}-01-01") & (data.index <= f"{window['test_year']}-12-31")
            
            train_data = data[train_mask].copy()
            test_data = data[test_mask].copy()
            
            print(f"  Train: {len(train_data)} bars")
            print(f"  Test: {len(test_data)} bars")
            
            # Optimize on training data
            best_params = self.optimize_on_train(train_data)
            
            if best_params is None:
                print(f"  WARNING: Could not optimize on training data")
                continue
            
            print(f"  Best params from training: SL={best_params['sl_mult']}x ATR, R:R={best_params['rr']}")
            
            # Test on unseen data
            test_data = self.calculate_indicators(test_data)
            test_trades = self.run_strategy(test_data, best_params)
            test_stats = self.calculate_stats(test_trades)
            
            print(f"\n  TEST RESULTS ({window['test_year']}):")
            print(f"    Trades: {test_stats['trades']}")
            if test_stats['trades'] > 0:
                print(f"    Win rate: {test_stats['win_rate']*100:.1f}%")
                print(f"    PF: {test_stats['pf']:.3f}")
                print(f"    Expectancy: {test_stats['expectancy']:.3f}R")
                print(f"    Total R: {test_stats['total_r']:.1f}")
            
            self.results.append({
                "window": window,
                "params": best_params,
                "test_stats": test_stats
            })
        
        # Summary
        print(f"\n{'='*60}")
        print("  WALK-FORWARD SUMMARY")
        print("="*60)
        
        if self.results:
            test_expectancies = [r["test_stats"]["expectancy"] for r in self.results if r["test_stats"]["trades"] > 0]
            test_pfs = [r["test_stats"]["pf"] for r in self.results if r["test_stats"]["trades"] > 0]
            
            print(f"\n  Windows completed: {len(self.results)}")
            print(f"  Windows with trades: {len(test_expectancies)}")
            
            if test_expectancies:
                print(f"\n  Test Period Performance:")
                print(f"    Mean expectancy: {np.mean(test_expectancies):.3f}R")
                print(f"    Median expectancy: {np.median(test_expectancies):.3f}R")
                print(f"    Std expectancy: {np.std(test_expectancies):.3f}R")
                print(f"    Min expectancy: {np.min(test_expectancies):.3f}R")
                print(f"    Max expectancy: {np.max(test_expectancies):.3f}R")
                
                print(f"\n    Mean PF: {np.mean(test_pfs):.3f}")
                print(f"    Min PF: {np.min(test_pfs):.3f}")
                
                # Count profitable periods
                profitable = sum(1 for e in test_expectancies if e > 0)
                total = len(test_expectancies)
                print(f"\n    Profitable periods: {profitable}/{total} ({profitable/total*100:.0f}%)")
                
                # Consistency score
                consistency = profitable / total
                print(f"    Consistency: {consistency*100:.0f}%")
            
            # Final verdict
            print(f"\n{'='*60}")
            print("  FINAL VERDICT")
            print("="*60)
            
            if test_expectancies:
                if (np.mean(test_expectancies) > 0.15 and
                    np.median(test_expectancies) > 0.1 and
                    profitable / total >= 0.6 and
                    np.mean(test_pfs) > 1.2):
                    print("  ? WALK-FORWARD VALIDATION PASSED")
                    print("  Strategy shows robust edge across multiple periods")
                else:
                    print("  ? WALK-FORWARD VALIDATION FAILED")
                    print("  Edge is not consistent across periods")
        
        return self.results
    
    def save_results(self):
        """Save walk-forward results."""
        results_dir = Path("research/walk_forward_results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = results_dir / f"walk_forward_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nResults saved to {filepath}")

if __name__ == "__main__":
    tester = WalkForwardTester()
    results = tester.run_walk_forward()
    tester.save_results()
