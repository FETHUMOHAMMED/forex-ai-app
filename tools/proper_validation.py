"""PROPER TIME-BASED VALIDATION - No Data Leakage."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from datetime import datetime
import json
from pathlib import Path

class ProperValidation:
    """Validates strategy with strict time-based separation."""
    
    def __init__(self):
        self.periods = {
            "train": ("2018-07-03", "2022-12-31"),
            "validation": ("2023-01-01", "2023-12-31"),
            "out_of_sample": ("2024-01-01", "2025-12-31"),
            "live_paper": ("2026-01-01", "2026-08-18")
        }
        
        self.results = {}
        self.strategy_params = None  # Will be set during training
        self.frozen = False  # Strategy becomes frozen after validation
        
    def load_data(self):
        """Load full historical data."""
        if not mt5.initialize():
            print("MT5 initialization failed")
            return None
        
        rates = mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 10000)
        mt5.shutdown()
        
        if rates is None:
            return None
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        data.set_index('timestamp', inplace=True)
        
        return data
    
    def split_data(self, data):
        """Split data into proper time periods."""
        splits = {}
        
        for period_name, (start, end) in self.periods.items():
            mask = (data.index >= start) & (data.index <= end)
            splits[period_name] = data[mask].copy()
            
            print(f"{period_name}: {len(splits[period_name])} bars")
        
        return splits
    
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
            # Session filter
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            # HTF bias
            bullish_bias = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
            
            # FVG detection
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
            return {"trades": 0}
        
        r_values = [t["r"] for t in trades]
        wins = sum(1 for r in r_values if r > 0)
        gross_profit = sum(r for r in r_values if r > 0)
        gross_loss = abs(sum(r for r in r_values if r < 0))
        
        return {
            "trades": len(r_values),
            "win_rate": wins / len(r_values),
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float('inf'),
            "expectancy": np.mean(r_values),
            "total_r": sum(r_values)
        }
    
    def train_phase(self, train_data):
        """TRAIN PHASE: Develop strategy on training data only."""
        print("\n" + "="*60)
        print("  TRAIN PHASE (2018-2022)")
        print("="*60)
        
        train_data = self.calculate_indicators(train_data)
        
        # Test different parameters on TRAIN data only
        param_variations = [
            {"sl_mult": 1.0, "rr": 2.0},
            {"sl_mult": 1.5, "rr": 2.0},
            {"sl_mult": 1.5, "rr": 2.5},
            {"sl_mult": 2.0, "rr": 2.0},
            {"sl_mult": 2.0, "rr": 2.5},
        ]
        
        best_params = None
        best_expectancy = -float('inf')
        
        for params in param_variations:
            trades = self.run_strategy(train_data, params)
            stats = self.calculate_stats(trades)
            
            print(f"\nParams: SL={params['sl_mult']}x ATR, R:R={params['rr']}")
            print(f"  Trades: {stats['trades']}")
            if stats['trades'] > 20:
                print(f"  Win rate: {stats['win_rate']*100:.1f}%")
                print(f"  PF: {stats['profit_factor']:.3f}")
                print(f"  Expectancy: {stats['expectancy']:.3f}R")
                
                # Select best based on expectancy
                if stats['expectancy'] > best_expectancy:
                    best_expectancy = stats['expectancy']
                    best_params = params
                    self.strategy_params = params
        
        print(f"\nBest parameters from TRAINING:")
        print(f"  SL: {best_params['sl_mult']}x ATR")
        print(f"  R:R: {best_params['rr']}")
        print(f"  Training expectancy: {best_expectancy:.3f}R")
        
        return best_params
    
    def validation_phase(self, validation_data, params):
        """VALIDATION PHASE: Confirm parameters on validation data."""
        print("\n" + "="*60)
        print("  VALIDATION PHASE (2023)")
        print("="*60)
        
        validation_data = self.calculate_indicators(validation_data)
        trades = self.run_strategy(validation_data, params)
        stats = self.calculate_stats(trades)
        
        print(f"\nValidation results:")
        print(f"  Trades: {stats['trades']}")
        if stats['trades'] > 0:
            print(f"  Win rate: {stats['win_rate']*100:.1f}%")
            print(f"  PF: {stats['profit_factor']:.3f}")
            print(f"  Expectancy: {stats['expectancy']:.3f}R")
        
        # Check if validation confirms training
        if stats['trades'] >= 10 and stats['expectancy'] > 0:
            self.frozen = True
            print(f"\n? Validation PASSED - Strategy FROZEN")
            print(f"  No more parameter changes allowed")
        else:
            print(f"\n? Validation FAILED - Return to training")
            print(f"  Strategy not ready for out-of-sample testing")
        
        return stats
    
    def out_of_sample_phase(self, oos_data, params):
        """OUT-OF-SAMPLE PHASE: Final test on untouched data."""
        print("\n" + "="*60)
        print("  OUT-OF-SAMPLE PHASE (2024-2025)")
        print("="*60)
        
        if not self.frozen:
            print("  ERROR: Strategy must pass validation first!")
            return None
        
        oos_data = self.calculate_indicators(oos_data)
        trades = self.run_strategy(oos_data, params)
        stats = self.calculate_stats(trades)
        
        print(f"\nOut-of-Sample results (UNSEEN DATA):")
        print(f"  Trades: {stats['trades']}")
        if stats['trades'] > 0:
            print(f"  Win rate: {stats['win_rate']*100:.1f}%")
            print(f"  PF: {stats['profit_factor']:.3f}")
            print(f"  Expectancy: {stats['expectancy']:.3f}R")
            
            # Statistical test
            r_values = [t["r"] for t in trades]
            t_stat, p_value = scipy_stats.ttest_1samp(r_values, 0)
            print(f"  P-value: {p_value:.4f}")
            print(f"  Significant: {'YES' if p_value < 0.05 else 'NO'}")
        
        return stats
    
    def live_paper_phase(self, live_data, params):
        """LIVE/PAPER PHASE: Current year performance."""
        print("\n" + "="*60)
        print("  LIVE/PAPER PHASE (2026)")
        print("="*60)
        
        live_data = self.calculate_indicators(live_data)
        trades = self.run_strategy(live_data, params)
        stats = self.calculate_stats(trades)
        
        print(f"\n2026 results (so far):")
        print(f"  Trades: {stats['trades']}")
        if stats['trades'] > 0:
            print(f"  Win rate: {stats['win_rate']*100:.1f}%")
            print(f"  PF: {stats['profit_factor']:.3f}")
            print(f"  Expectancy: {stats['expectancy']:.3f}R")
        
        return stats
    
    def run_full_validation(self):
        """Run the complete validation pipeline."""
        print("="*60)
        print("  PROPER TIME-BASED VALIDATION")
        print("  Train ? Validation ? Out-of-Sample ? Live")
        print("="*60)
        
        # Load data
        data = self.load_data()
        if data is None:
            return None
        
        # Split into periods
        splits = self.split_data(data)
        
        # Phase 1: Train (develop strategy)
        best_params = self.train_phase(splits["train"])
        
        # Phase 2: Validate (confirm parameters)
        validation_stats = self.validation_phase(splits["validation"], best_params)
        
        # Phase 3: Out-of-Sample (final test)
        oos_stats = self.out_of_sample_phase(splits["out_of_sample"], best_params)
        
        # Phase 4: Live/Paper (current year)
        live_stats = self.live_paper_phase(splits["live_paper"], best_params)
        
        # Summary
        print("\n" + "="*60)
        print("  VALIDATION SUMMARY")
        print("="*60)
        print(f"\nParameters: SL={best_params['sl_mult']}x ATR, R:R={best_params['rr']}")
        print(f"\nPhase Results:")
        print(f"  Train: {self.calculate_stats(self.run_strategy(self.calculate_indicators(splits['train']), best_params))['expectancy']:.3f}R")
        print(f"  Validation: {validation_stats['expectancy']:.3f}R")
        print(f"  Out-of-Sample: {oos_stats['expectancy']:.3f}R")
        print(f"  Live/Paper: {live_stats['expectancy']:.3f}R")
        
        # Final verdict
        print(f"\nFINAL VERDICT:")
        if (validation_stats['trades'] >= 10 and 
            oos_stats['trades'] >= 20 and 
            validation_stats['expectancy'] > 0 and 
            oos_stats['expectancy'] > 0):
            print("  ? STRATEGY VALIDATED ACROSS ALL TIME PERIODS")
            print("  ? Ready for forward testing")
        else:
            print("  ? STRATEGY FAILED VALIDATION")
            print("  ? Return to research phase")
        
        return {
            "params": best_params,
            "train": validation_stats,
            "validation": validation_stats,
            "oos": oos_stats,
            "live": live_stats
        }

if __name__ == "__main__":
    validator = ProperValidation()
    results = validator.run_full_validation()

