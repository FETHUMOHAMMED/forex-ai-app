"""MONTE CARLO ON WALK-FORWARD RESULTS - True Risk Assessment."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

class MonteCarloWalkForward:
    """Monte Carlo simulation on realistic walk-forward data."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        self.n_simulations = 10000
        
    def get_walk_forward_trades(self):
        """Get walk-forward test trades (realistic performance)."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        data.set_index('timestamp', inplace=True)
        
        # Calculate indicators
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean()
        
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        data['hour'] = data.index.hour
        data['bullish_fvg'] = (data['high'].shift(2) < data['low'])
        
        # Get walk-forward test periods (2023, 2024, 2025, 2026)
        test_periods = ['2023', '2024', '2025', '2026']
        
        trades = []
        
        for i in range(200, len(data)):
            # Only test periods
            year = str(data.index[i].year)
            if year not in test_periods:
                continue
            
            # Strategy conditions
            if not data['bullish_fvg'].iloc[i]:
                continue
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            hour = data['hour'].iloc[i]
            if not ((0 <= hour < 7) or (7 <= hour < 11) or (17 <= hour < 21)):
                continue
            
            # Execute trade
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * 2.0)
            tp = entry + (data['atr'].iloc[i] * 4.0)  # R:R 2.0
            
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({"r": -1, "date": data.index[i]})
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({"r": 2.0, "date": data.index[i]})
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({"r": r, "date": data.index[i]})
        
        return trades
    
    def run_monte_carlo(self, trades):
        """Run comprehensive Monte Carlo."""
        if not trades:
            return None
        
        r_values = [t["r"] for t in trades]
        n_trades = len(r_values)
        
        print(f"\n  Walk-forward trades: {n_trades}")
        print(f"  Historical expectancy: {np.mean(r_values):.3f}R")
        print(f"  Historical max DD: {self.calculate_drawdown(r_values):.1f}R")
        
        # Monte Carlo scenarios
        scenarios = {
            "Trade Order Randomization": self.mc_trade_order,
            "Slippage Variation": self.mc_slippage,
            "Spread Variation": self.mc_spread,
            "Missed Trades": self.mc_missed_trades,
            "Losing Streak Injection": self.mc_losing_streaks,
            "Parameter Drift": self.mc_parameter_drift,
            "Combined Worst Case": self.mc_combined_worst,
        }
        
        results = {}
        
        print(f"\n{'='*70}")
        print("  MONTE CARLO RESULTS (10,000 simulations each)")
        print("="*70)
        
        print(f"\n  {'Scenario':25s} {'Mean DD':>8s} {'P95 DD':>8s} {'P99 DD':>8s} {'Max Streak':>10s} {'P(Profit)':>10s}")
        print(f"  " + "-"*75)
        
        for name, scenario_func in scenarios.items():
            stats = scenario_func(r_values, n_trades)
            results[name] = stats
            
            print(f"  {name:25s} {stats['mean_dd']:7.1f}R {stats['p95_dd']:7.1f}R {stats['p99_dd']:7.1f}R {stats['max_streak']:9d} {stats['prob_profit']*100:9.1f}%")
        
        # Worst case analysis
        print(f"\n{'='*70}")
        print("  WORST CASE ANALYSIS")
        print("="*70)
        
        all_p99 = [stats["p99_dd"] for stats in results.values()]
        all_max_streaks = [stats["max_streak"] for stats in results.values()]
        
        worst_dd = max(all_p99)
        worst_streak = max(all_max_streaks)
        
        print(f"\n  Worst 99th percentile DD: {worst_dd:.1f}R")
        print(f"  Worst losing streak: {worst_streak} trades")
        
        # Position sizing implications
        print(f"\n{'='*70}")
        print("  POSITION SIZING IMPLICATIONS")
        print("="*70)
        
        for risk_pct in [0.25, 0.5, 0.75, 1.0]:
            worst_dd_pct = worst_dd * risk_pct
            print(f"\n  Risk {risk_pct:.2f}% per trade:")
            print(f"    Worst DD: {worst_dd_pct:.1f}% of account")
            
            if worst_dd_pct <= 10:
                print(f"    Status: SAFE ?")
            elif worst_dd_pct <= 15:
                print(f"    Status: ACCEPTABLE ?")
            elif worst_dd_pct <= 20:
                print(f"    Status: RISKY ??")
            else:
                print(f"    Status: DANGEROUS ?")
        
        # Recovery analysis
        print(f"\n{'='*70}")
        print("  RECOVERY ANALYSIS")
        print("="*70)
        
        expectancy = np.mean(r_values)
        print(f"\n  Expectancy: {expectancy:.3f}R per trade")
        print(f"  Trades per month: {n_trades / 48:.1f} (based on 4 years)")
        
        if expectancy > 0:
            recovery_trades = worst_dd / expectancy
            recovery_months = recovery_trades / (n_trades / 48)
            
            print(f"\n  After worst DD of {worst_dd:.1f}R:")
            print(f"    Trades to recover: {recovery_trades:.0f}")
            print(f"    Months to recover: {recovery_months:.1f}")
        
        return results
    
    def mc_trade_order(self, r_values, n_trades):
        """Randomize trade order."""
        max_dds = []
        max_streaks = []
        final_equities = []
        
        for _ in range(self.n_simulations):
            shuffled = np.random.permutation(r_values)
            max_dds.append(self.calculate_drawdown(shuffled))
            max_streaks.append(self.calculate_max_streak(shuffled))
            final_equities.append(np.sum(shuffled))
        
        return {
            "mean_dd": np.mean(max_dds),
            "p95_dd": np.percentile(max_dds, 95),
            "p99_dd": np.percentile(max_dds, 99),
            "max_streak": np.max(max_streaks),
            "prob_profit": (np.array(final_equities) > 0).mean()
        }
    
    def mc_slippage(self, r_values, n_trades):
        """Add random slippage."""
        max_dds = []
        max_streaks = []
        final_equities = []
        
        for _ in range(self.n_simulations):
            adjusted = []
            for r in r_values:
                slippage = np.random.exponential(0.8) / 30  # Convert to R
                adjusted.append(r - slippage)
            
            max_dds.append(self.calculate_drawdown(adjusted))
            max_streaks.append(self.calculate_max_streak(adjusted))
            final_equities.append(np.sum(adjusted))
        
        return {
            "mean_dd": np.mean(max_dds),
            "p95_dd": np.percentile(max_dds, 95),
            "p99_dd": np.percentile(max_dds, 99),
            "max_streak": np.max(max_streaks),
            "prob_profit": (np.array(final_equities) > 0).mean()
        }
    
    def mc_spread(self, r_values, n_trades):
        """Vary spread."""
        max_dds = []
        max_streaks = []
        final_equities = []
        
        for _ in range(self.n_simulations):
            adjusted = []
            for r in r_values:
                spread = np.random.uniform(0.5, 3.0) / 30
                adjusted.append(r - spread)
            
            max_dds.append(self.calculate_drawdown(adjusted))
            max_streaks.append(self.calculate_max_streak(adjusted))
            final_equities.append(np.sum(adjusted))
        
        return {
            "mean_dd": np.mean(max_dds),
            "p95_dd": np.percentile(max_dds, 95),
            "p99_dd": np.percentile(max_dds, 99),
            "max_streak": np.max(max_streaks),
            "prob_profit": (np.array(final_equities) > 0).mean()
        }
    
    def mc_missed_trades(self, r_values, n_trades):
        """Randomly miss trades."""
        max_dds = []
        max_streaks = []
        final_equities = []
        
        for _ in range(self.n_simulations):
            adjusted = [r for r in r_values if np.random.random() > 0.10]
            if adjusted:
                max_dds.append(self.calculate_drawdown(adjusted))
                max_streaks.append(self.calculate_max_streak(adjusted))
                final_equities.append(np.sum(adjusted))
            else:
                max_dds.append(0)
                max_streaks.append(0)
                final_equities.append(0)
        
        return {
            "mean_dd": np.mean(max_dds),
            "p95_dd": np.percentile(max_dds, 95),
            "p99_dd": np.percentile(max_dds, 99),
            "max_streak": np.max(max_streaks),
            "prob_profit": (np.array(final_equities) > 0).mean()
        }
    
    def mc_losing_streaks(self, r_values, n_trades):
        """Inject losing streaks."""
        max_dds = []
        max_streaks = []
        final_equities = []
        
        for _ in range(self.n_simulations):
            adjusted = r_values.copy()
            streak_len = np.random.randint(5, 13)
            streak_start = np.random.randint(0, max(1, len(adjusted) - streak_len))
            for i in range(streak_start, min(streak_start + streak_len, len(adjusted))):
                adjusted[i] = -1.0
            
            max_dds.append(self.calculate_drawdown(adjusted))
            max_streaks.append(self.calculate_max_streak(adjusted))
            final_equities.append(np.sum(adjusted))
        
        return {
            "mean_dd": np.mean(max_dds),
            "p95_dd": np.percentile(max_dds, 95),
            "p99_dd": np.percentile(max_dds, 99),
            "max_streak": np.max(max_streaks),
            "prob_profit": (np.array(final_equities) > 0).mean()
        }
    
    def mc_parameter_drift(self, r_values, n_trades):
        """Parameter drift."""
        max_dds = []
        max_streaks = []
        final_equities = []
        
        for _ in range(self.n_simulations):
            adjusted = []
            drift = np.random.uniform(0.8, 1.2)
            for r in r_values:
                adjusted.append(r * drift)
            
            max_dds.append(self.calculate_drawdown(adjusted))
            max_streaks.append(self.calculate_max_streak(adjusted))
            final_equities.append(np.sum(adjusted))
        
        return {
            "mean_dd": np.mean(max_dds),
            "p95_dd": np.percentile(max_dds, 95),
            "p99_dd": np.percentile(max_dds, 99),
            "max_streak": np.max(max_streaks),
            "prob_profit": (np.array(final_equities) > 0).mean()
        }
    
    def mc_combined_worst(self, r_values, n_trades):
        """Combine all adverse conditions."""
        max_dds = []
        max_streaks = []
        final_equities = []
        
        for _ in range(self.n_simulations):
            adjusted = []
            for r in r_values:
                # Add slippage
                slippage = np.random.exponential(0.8) / 30
                # Add spread
                spread = np.random.uniform(0.5, 3.0) / 30
                # Parameter drift
                drift = np.random.uniform(0.9, 1.1)
                adjusted.append((r * drift) - slippage - spread)
            
            # Inject losing streak
            streak_len = np.random.randint(5, 13)
            streak_start = np.random.randint(0, max(1, len(adjusted) - streak_len))
            for i in range(streak_start, min(streak_start + streak_len, len(adjusted))):
                adjusted[i] = -1.0
            
            max_dds.append(self.calculate_drawdown(adjusted))
            max_streaks.append(self.calculate_max_streak(adjusted))
            final_equities.append(np.sum(adjusted))
        
        return {
            "mean_dd": np.mean(max_dds),
            "p95_dd": np.percentile(max_dds, 95),
            "p99_dd": np.percentile(max_dds, 99),
            "max_streak": np.max(max_streaks),
            "prob_profit": (np.array(final_equities) > 0).mean()
        }
    
    def calculate_drawdown(self, r_values):
        """Calculate max drawdown."""
        if len(r_values) == 0:
            return 0
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        return np.max(drawdown)
    
    def calculate_max_streak(self, r_values):
        """Calculate max losing streak."""
        max_streak = 0
        current = 0
        for r in r_values:
            if r < 0:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return max_streak

if __name__ == "__main__":
    mc = MonteCarloWalkForward()
    trades = mc.get_walk_forward_trades()
    results = mc.run_monte_carlo(trades)

