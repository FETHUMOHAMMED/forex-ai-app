"""RESEARCH PIPELINE - Discovers and validates strategies."""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib

@dataclass
class ResearchConfig:
    """Configuration for research pipeline."""
    research_dir: Path = Path("research")
    data_dir: Path = Path("research/data")
    features_dir: Path = Path("research/features")
    strategies_dir: Path = Path("research/strategies")
    backtest_dir: Path = Path("research/backtest")
    validation_dir: Path = Path("research/validation")
    optimization_dir: Path = Path("research/optimization")
    walk_forward_dir: Path = Path("research/walk_forward")
    monte_carlo_dir: Path = Path("research/monte_carlo")
    reports_dir: Path = Path("research/reports")
    
    def __post_init__(self):
        """Create all directories."""
        for dir_path in [
            self.research_dir, self.data_dir, self.features_dir,
            self.strategies_dir, self.backtest_dir, self.validation_dir,
            self.optimization_dir, self.walk_forward_dir,
            self.monte_carlo_dir, self.reports_dir
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

class StrategyVersion:
    """Immutable strategy version that production can consume."""
    
    def __init__(self, strategy_id: str, parameters: Dict, 
                 validation_results: Dict):
        self.strategy_id = strategy_id
        self.parameters = parameters
        self.validation_results = validation_results
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.version_hash = self._generate_hash()
        
    def _generate_hash(self) -> str:
        """Generate immutable hash of strategy definition."""
        strategy_def = {
            "strategy_id": self.strategy_id,
            "parameters": self.parameters,
            "validation_results": self.validation_results
        }
        return hashlib.sha256(
            json.dumps(strategy_def, sort_keys=True).encode()
        ).hexdigest()
    
    def to_production_format(self) -> Dict:
        """Export strategy in production-ready format."""
        return {
            "strategy_id": self.strategy_id,
            "version": self.version_hash[:16],
            "parameters": self.parameters,
            "validation_summary": {
                "expectancy": self.validation_results.get("expectancy"),
                "profit_factor": self.validation_results.get("profit_factor"),
                "max_drawdown": self.validation_results.get("max_drawdown"),
                "win_rate": self.validation_results.get("win_rate"),
                "sample_size": self.validation_results.get("sample_size")
            },
            "created_at": self.created_at,
            "status": "VALIDATED" if self._is_validated() else "REJECTED"
        }
    
    def _is_validated(self) -> bool:
        """Check if strategy meets minimum validation criteria."""
        criteria = {
            "min_expectancy": 0.2,
            "min_profit_factor": 1.3,
            "max_drawdown": 0.15,
            "min_sample_size": 100
        }
        
        results = self.validation_results
        return all([
            results.get("expectancy", 0) >= criteria["min_expectancy"],
            results.get("profit_factor", 0) >= criteria["min_profit_factor"],
            results.get("max_drawdown", 0) <= criteria["max_drawdown"],
            results.get("sample_size", 0) >= criteria["min_sample_size"]
        ])

class ResearchPipeline:
    """Complete research pipeline from data to validated strategy."""
    
    def __init__(self, config: ResearchConfig = None):
        self.config = config or ResearchConfig()
        
    def run_pipeline(self, raw_data: pd.DataFrame) -> StrategyVersion:
        """Run complete research pipeline."""
        print("Starting research pipeline...")
        
        # Step 1: Data Preparation
        print("1. Preparing data...")
        clean_data = self._prepare_data(raw_data)
        
        # Step 2: Feature Engineering
        print("2. Generating features...")
        features = self._generate_features(clean_data)
        
        # Step 3: Strategy Definition
        print("3. Defining strategy...")
        strategy_params = self._define_strategy()
        
        # Step 4: Backtesting
        print("4. Running backtest...")
        backtest_results = self._run_backtest(features, strategy_params)
        
        # Step 5: Validation
        print("5. Validating results...")
        validation_results = self._validate(backtest_results)
        
        # Step 6: Walk-Forward Analysis
        print("6. Running walk-forward...")
        walk_forward_results = self._walk_forward(features, strategy_params)
        
        # Step 7: Monte Carlo Simulation
        print("7. Running Monte Carlo...")
        mc_results = self._monte_carlo(backtest_results)
        
        # Step 8: Final Validation
        print("8. Final validation...")
        final_results = self._final_validation(
            backtest_results, validation_results, 
            walk_forward_results, mc_results
        )
        
        # Step 9: Create Strategy Version
        print("9. Creating strategy version...")
        strategy = StrategyVersion(
            strategy_id="V4_LIQUIDITY_MSS",
            parameters=strategy_params,
            validation_results=final_results
        )
        
        # Step 10: Generate Report
        print("10. Generating report...")
        self._generate_report(strategy)
        
        return strategy
    
    def _prepare_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare and clean data."""
        data = raw_data.copy()
        
        # Remove duplicates
        data = data.drop_duplicates(subset=['timestamp'])
        
        # Sort by timestamp
        data = data.sort_values('timestamp')
        
        # Handle missing values
        data = data.ffill()
        
        # Remove outliers (prices > 5 std from mean)
        for col in ['open', 'high', 'low', 'close']:
            mean = data[col].mean()
            std = data[col].std()
            data = data[(data[col] > mean - 5*std) & (data[col] < mean + 5*std)]
        
        # Save cleaned data
        data.to_csv(self.config.data_dir / "clean_data.csv", index=False)
        
        return data
    
    def _generate_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate point-in-time features."""
        features = data.copy()
        
        # Trend features
        features['ema_50'] = features['close'].ewm(span=50, min_periods=50).mean()
        features['ema_200'] = features['close'].ewm(span=200, min_periods=200).mean()
        features['ema_ratio'] = features['ema_50'] / features['ema_200']
        
        # Volatility features
        features['atr_14'] = self._calculate_atr(features, 14)
        features['volatility_20'] = features['close'].pct_change().rolling(20).std()
        
        # Volume features
        if 'volume' in features.columns:
            features['volume_ma_20'] = features['volume'].rolling(20).mean()
            features['volume_ratio'] = features['volume'] / features['volume_ma_20']
        
        # Price action features
        features['range_pct'] = (features['high'] - features['low']) / features['close']
        features['body_pct'] = abs(features['close'] - features['open']) / features['close']
        features['upper_wick'] = (features['high'] - features[['open', 'close']].max(axis=1)) / features['close']
        features['lower_wick'] = (features[['open', 'close']].min(axis=1) - features['low']) / features['close']
        
        # Save features
        features.to_csv(self.config.features_dir / "features.csv", index=False)
        
        return features
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        
        return atr
    
    def _define_strategy(self) -> Dict:
        """Define strategy parameters."""
        return {
            "h4_ema_fast": 50,
            "h4_ema_slow": 200,
            "sweep_lookback": 50,
            "sweep_wick_ratio": 0.5,
            "mss_break_pips": 2.0,
            "fvg_min_size_pips": 3.0,
            "sl_buffer_pips": 1.5,
            "tp_rr_ratio": 2.0,
            "max_spread_pips": 1.5,
            "session_start": 7,
            "session_end": 11
        }
    
    def _run_backtest(self, features: pd.DataFrame, 
                      strategy_params: Dict) -> Dict:
        """Run backtest with strategy parameters."""
        # This is where Strategy V1 logic runs
        trades = []
        
        for i in range(200, len(features)):
            # Check H4 bias
            if features['ema_50'].iloc[i] > features['ema_200'].iloc[i]:
                direction = "BUY"
            elif features['ema_50'].iloc[i] < features['ema_200'].iloc[i]:
                direction = "SELL"
            else:
                continue
            
            # Check for liquidity sweep
            lookback = features.iloc[i-50:i]
            if direction == "BUY":
                recent_low = lookback['low'].min()
                if features['low'].iloc[i] < recent_low:
                    # Check wick ratio
                    candle_range = features['high'].iloc[i] - features['low'].iloc[i]
                    lower_wick = features['close'].iloc[i] - features['low'].iloc[i]
                    if candle_range > 0 and lower_wick / candle_range >= 0.5:
                        # Check FVG
                        if i >= 2:
                            if features['high'].iloc[i-2] < features['low'].iloc[i]:
                                # Entry signal
                                entry = features['close'].iloc[i]
                                sl = features['low'].iloc[i-2] - 0.00015
                                tp = entry + (entry - sl) * 2
                                
                                # Simulate trade outcome
                                outcome = self._simulate_trade(
                                    features, i, entry, sl, tp, direction
                                )
                                trades.append(outcome)
            
            elif direction == "SELL":
                recent_high = lookback['high'].max()
                if features['high'].iloc[i] > recent_high:
                    candle_range = features['high'].iloc[i] - features['low'].iloc[i]
                    upper_wick = features['high'].iloc[i] - features['close'].iloc[i]
                    if candle_range > 0 and upper_wick / candle_range >= 0.5:
                        if i >= 2:
                            if features['low'].iloc[i-2] > features['high'].iloc[i]:
                                entry = features['close'].iloc[i]
                                sl = features['high'].iloc[i-2] + 0.00015
                                tp = entry - (sl - entry) * 2
                                
                                outcome = self._simulate_trade(
                                    features, i, entry, sl, tp, direction
                                )
                                trades.append(outcome)
        
        return self._calculate_trade_statistics(trades)
    
    def _simulate_trade(self, data: pd.DataFrame, entry_idx: int,
                        entry: float, sl: float, tp: float, 
                        direction: str) -> Dict:
        """Simulate trade outcome."""
        for j in range(entry_idx + 1, min(entry_idx + 1000, len(data))):
            if direction == "BUY":
                if data['low'].iloc[j] <= sl:
                    return {"result": "LOSS", "r": -1.0}
                elif data['high'].iloc[j] >= tp:
                    return {"result": "WIN", "r": 2.0}
            else:  # SELL
                if data['high'].iloc[j] >= sl:
                    return {"result": "LOSS", "r": -1.0}
                elif data['low'].iloc[j] <= tp:
                    return {"result": "WIN", "r": 2.0}
        
        # Timeout - close at market
        exit_price = data['close'].iloc[min(entry_idx + 1000, len(data)-1)]
        if direction == "BUY":
            r = (exit_price - entry) / (entry - sl)
        else:
            r = (entry - exit_price) / (sl - entry)
        return {"result": "TIMEOUT", "r": r}
    
    def _calculate_trade_statistics(self, trades: List[Dict]) -> Dict:
        """Calculate comprehensive trade statistics."""
        if not trades:
            return {
                "sample_size": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "expectancy": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0
            }
        
        r_values = [t["r"] for t in trades]
        wins = [r for r in r_values if r > 0]
        losses = [r for r in r_values if r < 0]
        
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        
        # Calculate drawdown
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown)
        
        return {
            "sample_size": len(trades),
            "win_rate": len(wins) / len(trades),
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float('inf'),
            "expectancy": np.mean(r_values),
            "max_drawdown": max_drawdown,
            "sharpe_ratio": np.mean(r_values) / (np.std(r_values) + 1e-10),
            "total_r": sum(r_values),
            "best_trade": max(r_values),
            "worst_trade": min(r_values),
            "avg_win": np.mean(wins) if wins else 0,
            "avg_loss": np.mean(losses) if losses else 0,
            "max_consecutive_losses": self._max_consecutive_losses(r_values)
        }
    
    def _max_consecutive_losses(self, r_values: List[float]) -> int:
        """Calculate maximum consecutive losses."""
        max_losses = 0
        current_losses = 0
        
        for r in r_values:
            if r < 0:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0
        
        return max_losses
    
    def _validate(self, backtest_results: Dict) -> Dict:
        """Validate backtest results."""
        validation = {
            "backtest": backtest_results,
            "out_of_sample": None,
            "walk_forward": None,
            "monte_carlo": None,
            "passed": False
        }
        
        # Check minimum criteria
        if backtest_results["sample_size"] >= 100:
            if backtest_results["expectancy"] >= 0.2:
                if backtest_results["profit_factor"] >= 1.3:
                    if backtest_results["max_drawdown"] <= 15:
                        validation["passed"] = True
        
        return validation
    
    def _walk_forward(self, features: pd.DataFrame, 
                      strategy_params: Dict) -> Dict:
        """Walk-forward analysis."""
        # Split data into multiple periods
        n_splits = 5
        split_size = len(features) // n_splits
        results = []
        
        for i in range(n_splits):
            train_start = i * split_size
            train_end = (i + 1) * split_size
            test_start = train_end
            test_end = min(test_start + split_size, len(features))
            
            train_data = features.iloc[train_start:train_end]
            test_data = features.iloc[test_start:test_end]
            
            # Train on training period
            train_results = self._run_backtest(train_data, strategy_params)
            
            # Test on out-of-sample period
            test_results = self._run_backtest(test_data, strategy_params)
            
            results.append({
                "period": i + 1,
                "train_results": train_results,
                "test_results": test_results,
                "oos_performance": test_results["expectancy"] - train_results["expectancy"]
            })
        
        return {
            "n_splits": n_splits,
            "periods": results,
            "avg_oos_degradation": np.mean([r["oos_performance"] for r in results]),
            "worst_period": min(results, key=lambda x: x["test_results"]["expectancy"])
        }
    
    def _monte_carlo(self, backtest_results: Dict, n_simulations: int = 1000) -> Dict:
        """Monte Carlo simulation."""
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
        }
    
    def _final_validation(self, backtest: Dict, validation: Dict,
                          walk_forward: Dict, monte_carlo: Dict) -> Dict:
        """Combine all validation results."""
        return {
            "backtest": backtest,
            "validation_passed": validation["passed"],
            "walk_forward": walk_forward,
            "monte_carlo": monte_carlo,
            "expectancy": backtest["expectancy"],
            "profit_factor": backtest["profit_factor"],
            "max_drawdown": backtest["max_drawdown"],
            "win_rate": backtest["win_rate"],
            "sample_size": backtest["sample_size"],
            "sharpe_ratio": backtest["sharpe_ratio"]
        }
    
    def _generate_report(self, strategy: StrategyVersion):
        """Generate research report."""
        report_path = self.config.reports_dir / f"{strategy.strategy_id}_{strategy.version_hash[:8]}.json"
        
        report = strategy.to_production_format()
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"Report saved to {report_path}")

if __name__ == "__main__":
    # Test the research pipeline
    pipeline = ResearchPipeline()
    
    # Create sample data
    dates = pd.date_range('2026-01-01', '2026-08-18', freq='5min')
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 101,
        'low': np.random.randn(len(dates)).cumsum() + 99,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1, 100, len(dates)),
    })
    
    # Run pipeline
    strategy = pipeline.run_pipeline(sample_data)
    
    print("\n" + "="*60)
    print("RESEARCH PIPELINE COMPLETE")
    print("="*60)
    print(f"Strategy ID: {strategy.strategy_id}")
    print(f"Version Hash: {strategy.version_hash[:16]}")
    print(f"Status: {strategy.to_production_format()['status']}")



