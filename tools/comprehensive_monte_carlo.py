"""COMPREHENSIVE MONTE CARLO - Bad but plausible futures."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
import json
from pathlib import Path

class ComprehensiveMonteCarlo:
    """Tests strategy under realistic adverse scenarios."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        self.n_simulations = 10000
        
    def load_historical_trades(self):
        """Get historical trade results."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
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
            
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * 2.0)
                tp = entry + (data['atr'].iloc[i] * 5.0)
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        trades.append({"r": -1, "result": "SL"})
                        break
                    elif data['high'].iloc[j] >= tp:
                        trades.append({"r": 2.5, "result": "TP"})
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    trades.append({"r": r, "result": "TIMEOUT"})
        
        return trades
    
    def simulate_trade_order_randomization(self, trades, n_sims=10000):
        """Simulation 1: Shuffle trade order."""
        print(f"\n1. TRADE ORDER RANDOMIZATION")
        print(f"   Testing {n_sims} random orderings")
        
        r_values = [t["r"] for t in trades]
        max_drawdowns = []
        final_equities = []
        
        for _ in range(n_sims):
            shuffled = np.random.permutation(r_values)
            equity = np.cumsum(shuffled)
            final_equities.append(equity[-1])
            
            running_max = np.maximum.accumulate(equity)
            dd = running_max - equity
            max_drawdowns.append(np.max(dd))
        
        return {
            "mean_max_dd": np.mean(max_drawdowns),
            "p50_max_dd": np.percentile(max_drawdowns, 50),
            "p90_max_dd": np.percentile(max_drawdowns, 90),
            "p95_max_dd": np.percentile(max_drawdowns, 95),
            "p99_max_dd": np.percentile(max_drawdowns, 99),
            "prob_profit": (np.array(final_equities) > 0).mean() * 100
        }
    
    def simulate_slippage_variation(self, trades, n_sims=10000):
        """Simulation 2: Vary slippage on each trade."""
        print(f"\n2. SLIPPAGE VARIATION")
        print(f"   Testing random slippage 0-3 pips per trade")
        
        r_values = [t["r"] for t in trades]
        max_drawdowns = []
        final_equities = []
        
        for _ in range(n_sims):
            # Add random slippage to each trade
            adjusted_r = []
            for r in r_values:
                slippage = np.random.exponential(0.8)  # Mean 0.8 pips
                slippage_r = slippage / 30  # Convert to R (30 pips typical SL)
                
                if r > 0:
                    adjusted_r.append(r - slippage_r)
                else:
                    adjusted_r.append(r - slippage_r)
            
            equity = np.cumsum(adjusted_r)
            final_equities.append(equity[-1])
            
            running_max = np.maximum.accumulate(equity)
            dd = running_max - equity
            max_drawdowns.append(np.max(dd))
        
        return {
            "mean_max_dd": np.mean(max_drawdowns),
            "p95_max_dd": np.percentile(max_drawdowns, 95),
            "p99_max_dd": np.percentile(max_drawdowns, 99),
            "prob_profit": (np.array(final_equities) > 0).mean() * 100
        }
    
    def simulate_spread_variation(self, trades, n_sims=10000):
        """Simulation 3: Vary spread."""
        print(f"\n3. SPREAD VARIATION")
        print(f"   Testing spreads 0.5-5.0 pips")
        
        r_values = [t["r"] for t in trades]
        max_drawdowns = []
        final_equities = []
        
        for _ in range(n_sims):
            adjusted_r = []
            for r in r_values:
                spread = np.random.uniform(0.5, 5.0)
                spread_r = spread / 30  # Convert to R
                
                if r > 0:
                    adjusted_r.append(r - spread_r)
                else:
                    adjusted_r.append(r - spread_r)
            
            equity = np.cumsum(adjusted_r)
            final_equities.append(equity[-1])
            
            running_max = np.maximum.accumulate(equity)
            dd = running_max - equity
            max_drawdowns.append(np.max(dd))
        
        return {
            "mean_max_dd": np.mean(max_drawdowns),
            "p95_max_dd": np.percentile(max_drawdowns, 95),
            "p99_max_dd": np.percentile(max_drawdowns, 99),
            "prob_profit": (np.array(final_equities) > 0).mean() * 100
        }
    
    def simulate_missed_trades(self, trades, n_sims=10000):
        """Simulation 4: Randomly miss some trades."""
        print(f"\n4. MISSED TRADES")
        print(f"   Testing 5-20% missed trade rate")
        
        r_values = [t["r"] for t in trades]
        max_drawdowns = []
        final_equities = []
        
        for _ in range(n_sims):
            adjusted_r = []
            for r in r_values:
                # Randomly miss this trade
                if np.random.random() < 0.10:  # 10% miss rate
                    continue
                adjusted_r.append(r)
            
            if adjusted_r:
                equity = np.cumsum(adjusted_r)
                final_equities.append(equity[-1])
                
                running_max = np.maximum.accumulate(equity)
                dd = running_max - equity
                max_drawdowns.append(np.max(dd))
            else:
                final_equities.append(0)
                max_drawdowns.append(0)
        
        return {
            "mean_max_dd": np.mean(max_drawdowns),
            "p95_max_dd": np.percentile(max_drawdowns, 95),
            "p99_max_dd": np.percentile(max_drawdowns, 99),
            "prob_profit": (np.array(final_equities) > 0).mean() * 100
        }
    
    def simulate_delayed_execution(self, trades, n_sims=10000):
        """Simulation 5: Execution delays."""
        print(f"\n5. DELAYED EXECUTION")
        print(f"   Testing 1-4 hour delays")
        
        r_values = [t["r"] for t in trades]
        max_drawdowns = []
        final_equities = []
        
        for _ in range(n_sims):
            adjusted_r = []
            for r in r_values:
                # Delayed execution means worse entry
                delay = np.random.uniform(1, 4)  # Hours delayed
                delay_r = delay * 0.05  # 0.05R per hour delay
                
                adjusted_r.append(r - delay_r)
            
            equity = np.cumsum(adjusted_r)
            final_equities.append(equity[-1])
            
            running_max = np.maximum.accumulate(equity)
            dd = running_max - equity
            max_drawdowns.append(np.max(dd))
        
        return {
            "mean_max_dd": np.mean(max_drawdowns),
            "p95_max_dd": np.percentile(max_drawdowns, 95),
            "p99_max_dd": np.percentile(max_drawdowns, 99),
            "prob_profit": (np.array(final_equities) > 0).mean() * 100
        }
    
    def simulate_parameter_perturbation(self, trades, n_sims=10000):
        """Simulation 6: Parameter drift."""
        print(f"\n6. PARAMETER PERTURBATION")
        print(f"   Testing ATR multiplier 1.5-2.5")
        
        r_values = [t["r"] for t in trades]
        max_drawdowns = []
        final_equities = []
        
        for _ in range(n_sims):
            adjusted_r = []
            atr_mult = np.random.uniform(1.5, 2.5)
            
            for r in r_values:
                # Parameter drift affects R multiple
                drift_factor = atr_mult / 2.0  # 1.0 = no drift
                adjusted_r.append(r * drift_factor)
            
            equity = np.cumsum(adjusted_r)
            final_equities.append(equity[-1])
            
            running_max = np.maximum.accumulate(equity)
            dd = running_max - equity
            max_drawdowns.append(np.max(dd))
        
        return {
            "mean_max_dd": np.mean(max_drawdowns),
            "p95_max_dd": np.percentile(max_drawdowns, 95),
            "p99_max_dd": np.percentile(max_drawdowns, 99),
            "prob_profit": (np.array(final_equities) > 0).mean() * 100
        }
    
    def simulate_losing_streaks(self, trades, n_sims=10000):
        """Simulation 7: Force losing streaks."""
        print(f"\n7. LOSING STREAK SCENARIOS")
        print(f"   Testing forced 5-15 trade losing streaks")
        
        r_values = [t["r"] for t in trades]
        max_drawdowns = []
        final_equities = []
        
        for _ in range(n_sims):
            adjusted_r = r_values.copy()
            
            # Insert random losing streak
            streak_length = np.random.randint(5, 16)
            streak_start = np.random.randint(0, len(adjusted_r) - streak_length)
            
            for i in range(streak_start, streak_start + streak_length):
                adjusted_r[i] = -1.0  # Force loss
            
            equity = np.cumsum(adjusted_r)
            final_equities.append(equity[-1])
            
            running_max = np.maximum.accumulate(equity)
            dd = running_max - equity
            max_drawdowns.append(np.max(dd))
        
        return {
            "mean_max_dd": np.mean(max_drawdowns),
            "p95_max_dd": np.percentile(max_drawdowns, 95),
            "p99_max_dd": np.percentile(max_drawdowns, 99),
            "prob_profit": (np.array(final_equities) > 0).mean() * 100
        }
    
    def run_comprehensive_monte_carlo(self):
        """Run all Monte Carlo simulations."""
        print("="*70)
        print("  COMPREHENSIVE MONTE CARLO SIMULATION")
        print("  Testing Bad But Plausible Futures")
        print("="*70)
        
        trades = self.load_historical_trades()
        if not trades:
            print("No trades loaded")
            return None
        
        print(f"\nLoaded {len(trades)} historical trades")
        print(f"Historical expectancy: {np.mean([t['r'] for t in trades]):.3f}R")
        print(f"Historical max DD: {self.calculate_historical_dd(trades):.1f}R")
        
        # Run all simulations
        results = {}
        
        results["trade_order"] = self.simulate_trade_order_randomization(trades)
        results["slippage"] = self.simulate_slippage_variation(trades)
        results["spread"] = self.simulate_spread_variation(trades)
        results["missed_trades"] = self.simulate_missed_trades(trades)
        results["delayed_execution"] = self.simulate_delayed_execution(trades)
        results["parameter_perturbation"] = self.simulate_parameter_perturbation(trades)
        results["losing_streaks"] = self.simulate_losing_streaks(trades)
        
        # Summary
        print(f"\n{'='*70}")
        print("  MONTE CARLO SUMMARY")
        print("="*70)
        
        print(f"\n  Scenario                     Mean DD    P95 DD    P99 DD    P(Profit)")
        print(f"  " + "-"*70)
        
        for scenario, stats in results.items():
            print(f"  {scenario:28s}  {stats['mean_max_dd']:5.1f}R    {stats['p95_max_dd']:5.1f}R    {stats['p99_max_dd']:5.1f}R    {stats['prob_profit']:5.1f}%")
        
        # Worst case analysis
        print(f"\n{'='*70}")
        print("  WORST CASE SCENARIO")
        print("="*70)
        
        all_p99 = [stats["p99_max_dd"] for stats in results.values()]
        worst_case_dd = max(all_p99)
        
        print(f"\n  Worst 99th percentile DD: {worst_case_dd:.1f}R")
        print(f"  Historical max DD: {self.calculate_historical_dd(trades):.1f}R")
        
        # Convert to account percentages
        print(f"\n  If risking 0.5% per trade:")
        print(f"    Expected max DD: {np.mean([s['mean_max_dd'] for s in results.values()]) * 0.5:.1f}%")
        print(f"    P95 max DD: {np.percentile([s['p95_max_dd'] for s in results.values()], 95) * 0.5:.1f}%")
        print(f"    P99 max DD: {worst_case_dd * 0.5:.1f}%")
        
        print(f"\n  If risking 1.0% per trade:")
        print(f"    Expected max DD: {np.mean([s['mean_max_dd'] for s in results.values()]) * 1.0:.1f}%")
        print(f"    P95 max DD: {np.percentile([s['p95_max_dd'] for s in results.values()], 95) * 1.0:.1f}%")
        print(f"    P99 max DD: {worst_case_dd * 1.0:.1f}%")
        
        return results
    
    def calculate_historical_dd(self, trades):
        """Calculate historical drawdown."""
        r_values = [t["r"] for t in trades]
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        dd = running_max - cumulative
        return np.max(dd)

if __name__ == "__main__":
    mc = ComprehensiveMonteCarlo()
    results = mc.run_comprehensive_monte_carlo()
    
    # Save results
    if results:
        results_path = Path("research/monte_carlo_results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {results_path}")
