"""Fix Monte Carlo simulation to handle negative Sharpe ratios."""
from pathlib import Path

# Read the file
file_path = Path("packages/research/research_pipeline.py")
content = file_path.read_text()

# Find and replace the problematic Monte Carlo code
old_code = """    def _monte_carlo(self, backtest_results: Dict, n_simulations: int = 1000) -> Dict:
        \"\"\"Monte Carlo simulation.\"\"\"
        if backtest_results["sample_size"] == 0:
            return {}
        
        # Generate random trade sequences
        r_values = np.random.normal(
            backtest_results["expectancy"],
            backtest_results["sharpe_ratio"],
            size=(n_simulations, backtest_results["sample_size"])
        )
        
        # Calculate statistics for each simulation
        final_equities = np.cumsum(r_values, axis=1)[:, -1]
        max_drawdowns = []
        
        for sim in r_values:
            cumulative = np.cumsum(sim)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = running_max - cumulative
            max_drawdowns.append(np.max(drawdown))
        
        return {
            "n_simulations": n_simulations,
            "mean_final_equity": np.mean(final_equities),
            "std_final_equity": np.std(final_equities),
            "p5_final_equity": np.percentile(final_equities, 5),
            "p95_final_equity": np.percentile(final_equities, 95),
            "mean_max_drawdown": np.mean(max_drawdowns),
            "p95_max_drawdown": np.percentile(max_drawdowns, 95),
            "probability_of_profit": (final_equities > 0).mean()
        }"""

new_code = """    def _monte_carlo(self, backtest_results: Dict, n_simulations: int = 1000) -> Dict:
        \"\"\"Monte Carlo simulation.\"\"\"
        if backtest_results["sample_size"] == 0:
            return {
                "n_simulations": 0,
                "mean_final_equity": 0,
                "std_final_equity": 0,
                "p5_final_equity": 0,
                "p95_final_equity": 0,
                "mean_max_drawdown": 0,
                "p95_max_drawdown": 0,
                "probability_of_profit": 0,
                "note": "No trades to simulate"
            }
        
        # Use absolute value for scale (std dev must be positive)
        scale = abs(backtest_results["sharpe_ratio"]) if backtest_results["sharpe_ratio"] != 0 else 1.0
        mean = backtest_results["expectancy"]
        
        # Generate random trade sequences
        r_values = np.random.normal(
            mean,
            scale,
            size=(n_simulations, backtest_results["sample_size"])
        )
        
        # Calculate statistics for each simulation
        final_equities = np.cumsum(r_values, axis=1)[:, -1]
        max_drawdowns = []
        
        for sim in r_values:
            cumulative = np.cumsum(sim)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = running_max - cumulative
            max_drawdowns.append(np.max(drawdown))
        
        return {
            "n_simulations": n_simulations,
            "mean_final_equity": np.mean(final_equities),
            "std_final_equity": np.std(final_equities),
            "p5_final_equity": np.percentile(final_equities, 5),
            "p95_final_equity": np.percentile(final_equities, 95),
            "mean_max_drawdown": np.mean(max_drawdowns),
            "p95_max_drawdown": np.percentile(max_drawdowns, 95),
            "probability_of_profit": (final_equities > 0).mean(),
            "note": "Using absolute Sharpe ratio for simulation scale" if backtest_results["sharpe_ratio"] < 0 else "Normal simulation"
        }"""

# Apply the replacement
content = content.replace(old_code, new_code)

# Write back
file_path.write_text(content)
print("Fixed Monte Carlo simulation")
