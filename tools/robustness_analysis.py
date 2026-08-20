"""PARAMETER ROBUSTNESS ANALYSIS - Find plateaus, not peaks."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
import json
from pathlib import Path

class RobustnessAnalyzer:
    """Tests if strategy works across parameter ranges, not just single values."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
    def load_data(self):
        """Load historical data."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        if rates is None:
            return None
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        return data
    
    def calculate_indicators(self, data, ema_fast=50, ema_slow=200, atr_period=14):
        """Calculate indicators with given parameters."""
        df = data.copy()
        df['ema_fast'] = df['close'].ewm(span=ema_fast).mean()
        df['ema_slow'] = df['close'].ewm(span=ema_slow).mean()
        
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(atr_period).mean()
        
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        return df
    
    def run_strategy(self, data, sl_mult, tp_rr, ema_fast=50, ema_slow=200):
        """Run strategy with specific parameters."""
        trades = []
        
        for i in range(200, len(data)):
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            # Long only
            if data['ema_fast'].iloc[i] <= data['ema_slow'].iloc[i]:
                continue
            
            if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * sl_mult)
                tp = entry + (data['atr'].iloc[i] * sl_mult * tp_rr)
                
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
    
    def calculate_stats(self, trades):
        """Calculate statistics."""
        if not trades:
            return {"trades": 0, "win_rate": 0, "pf": 0, "expectancy": 0}
        
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
    
    def test_atr_robustness(self, data):
        """Test different ATR multipliers."""
        print("="*70)
        print("  ATR MULTIPLIER ROBUSTNESS")
        print("="*70)
        
        atr_values = [1.0, 1.3, 1.5, 1.7, 1.8, 1.9, 2.0, 2.2, 2.5, 3.0]
        results = []
        
        print(f"\n  ATR    Trades  WinRate  PF      Expectancy")
        print(f"  " + "-"*55)
        
        for sl_mult in atr_values:
            trades = self.run_strategy(data, sl_mult, 2.5)
            stats = self.calculate_stats(trades)
            
            results.append({
                "atr_mult": sl_mult,
                **stats
            })
            
            print(f"  {sl_mult:.1f}x   {stats['trades']:3d}     {stats['win_rate']*100:5.1f}%  {stats['pf']:6.3f}  {stats['expectancy']:+.3f}R")
        
        # Check for plateau
        profitable_values = [r for r in results if r["expectancy"] > 0.2]
        
        print(f"\n  Robustness Analysis:")
        print(f"  Values tested: {len(atr_values)}")
        print(f"  Profitable (exp > 0.2R): {len(profitable_values)}")
        
        if len(profitable_values) >= 5:
            print(f"  ROBUST PLATEAU FOUND ?")
            print(f"  Strategy works across multiple ATR values")
        elif len(profitable_values) >= 3:
            print(f"  MODERATE ROBUSTNESS ?")
            print(f"  Some parameter sensitivity")
        else:
            print(f"  WEAK ROBUSTNESS ?")
            print(f"  Strategy too sensitive to ATR")
        
        return results
    
    def test_rr_robustness(self, data):
        """Test different R:R ratios."""
        print(f"\n{'='*70}")
        print("  R:R RATIO ROBUSTNESS")
        print("="*70)
        
        rr_values = [1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0, 3.5]
        results = []
        
        print(f"\n  R:R    Trades  WinRate  PF      Expectancy")
        print(f"  " + "-"*55)
        
        for rr in rr_values:
            trades = self.run_strategy(data, 2.0, rr)
            stats = self.calculate_stats(trades)
            
            results.append({
                "rr": rr,
                **stats
            })
            
            print(f"  {rr:.1f}    {stats['trades']:3d}     {stats['win_rate']*100:5.1f}%  {stats['pf']:6.3f}  {stats['expectancy']:+.3f}R")
        
        profitable_values = [r for r in results if r["expectancy"] > 0.2]
        
        print(f"\n  Robustness Analysis:")
        print(f"  Values tested: {len(rr_values)}")
        print(f"  Profitable (exp > 0.2R): {len(profitable_values)}")
        
        if len(profitable_values) >= 5:
            print(f"  ROBUST PLATEAU FOUND ?")
        elif len(profitable_values) >= 3:
            print(f"  MODERATE ROBUSTNESS ?")
        else:
            print(f"  WEAK ROBUSTNESS ?")
        
        return results
    
    def test_ema_robustness(self, data):
        """Test different EMA combinations."""
        print(f"\n{'='*70}")
        print("  EMA COMBINATION ROBUSTNESS")
        print("="*70)
        
        ema_combos = [
            (20, 100), (30, 150), (40, 200),
            (50, 200), (60, 250), (50, 150)
        ]
        
        results = []
        
        print(f"\n  EMA      Trades  WinRate  PF      Expectancy")
        print(f"  " + "-"*55)
        
        for fast, slow in ema_combos:
            data_with_ema = self.calculate_indicators(data, fast, slow)
            trades = self.run_strategy(data_with_ema, 2.0, 2.5, fast, slow)
            stats = self.calculate_stats(trades)
            
            results.append({
                "ema_fast": fast,
                "ema_slow": slow,
                **stats
            })
            
            print(f"  {fast}/{slow}   {stats['trades']:3d}     {stats['win_rate']*100:5.1f}%  {stats['pf']:6.3f}  {stats['expectancy']:+.3f}R")
        
        profitable_values = [r for r in results if r["expectancy"] > 0.2]
        
        print(f"\n  Robustness Analysis:")
        print(f"  Combos tested: {len(ema_combos)}")
        print(f"  Profitable (exp > 0.2R): {len(profitable_values)}")
        
        if len(profitable_values) >= 4:
            print(f"  ROBUST ACROSS EMA COMBINATIONS ?")
        elif len(profitable_values) >= 2:
            print(f"  MODERATE ROBUSTNESS ?")
        else:
            print(f"  WEAK ROBUSTNESS ?")
        
        return results
    
    def test_session_robustness(self, data):
        """Test different session windows."""
        print(f"\n{'='*70}")
        print("  SESSION WINDOW ROBUSTNESS")
        print("="*70)
        
        sessions = [
            ("London", 7, 11),
            ("London+1", 7, 12),
            ("Early London", 6, 10),
            ("Late London", 8, 12),
            ("Extended", 6, 13),
        ]
        
        results = []
        
        print(f"\n  Session    Trades  WinRate  PF      Expectancy")
        print(f"  " + "-"*55)
        
        for session_name, start, end in sessions:
            # Run strategy with modified session
            trades = []
            
            for i in range(200, len(data)):
                hour = data['hour'].iloc[i]
                if not (start <= hour <= end):
                    continue
                
                if data['ema_fast'].iloc[i] <= data['ema_slow'].iloc[i]:
                    continue
                
                if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry - (data['atr'].iloc[i] * 2.0)
                    tp = entry + (data['atr'].iloc[i] * 5.0)
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['low'].iloc[j] <= sl:
                            trades.append({"r": -1})
                            break
                        elif data['high'].iloc[j] >= tp:
                            trades.append({"r": 2.5})
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (exit_price - entry) / (entry - sl)
                        trades.append({"r": r})
            
            stats = self.calculate_stats(trades)
            results.append({"session": session_name, **stats})
            
            print(f"  {session_name:12s}  {stats['trades']:3d}     {stats['win_rate']*100:5.1f}%  {stats['pf']:6.3f}  {stats['expectancy']:+.3f}R")
        
        profitable_values = [r for r in results if r["expectancy"] > 0.2]
        
        print(f"\n  Robustness Analysis:")
        print(f"  Sessions tested: {len(sessions)}")
        print(f"  Profitable: {len(profitable_values)}")
        
        if len(profitable_values) >= 3:
            print(f"  ROBUST ACROSS SESSIONS ?")
        else:
            print(f"  SESSION SENSITIVE ?")
        
        return results
    
    def run_full_analysis(self):
        """Run complete robustness analysis."""
        print("="*70)
        print("  PARAMETER ROBUSTNESS ANALYSIS")
        print("  Looking for plateaus, not peaks")
        print("="*70)
        
        data = self.load_data()
        if data is None:
            return None
        
        data = self.calculate_indicators(data)
        
        # Test all parameter dimensions
        atr_results = self.test_atr_robustness(data)
        rr_results = self.test_rr_robustness(data)
        ema_results = self.test_ema_robustness(data)
        session_results = self.test_session_robustness(data)
        
        # Summary
        print(f"\n{'='*70}")
        print("  ROBUSTNESS SUMMARY")
        print("="*70)
        
        # Collect all profitable parameter values
        all_results = {
            "atr": atr_results,
            "rr": rr_results,
            "ema": ema_results,
            "session": session_results
        }
        
        # Save results
        results_path = Path("research/robustness_results.json")
        with open(results_path, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        
        print(f"\nResults saved to {results_path}")
        print(f"\n  Key Takeaway:")
        print(f"  A robust strategy works across multiple parameter values.")
        print(f"  A fragile strategy only works at one 'perfect' setting.")
        
        return all_results

if __name__ == "__main__":
    analyzer = RobustnessAnalyzer()
    results = analyzer.run_full_analysis()
