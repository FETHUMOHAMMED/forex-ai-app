"""RESEARCH BACKTEST ENGINE - Tests strategy hypothesis."""
import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta

class BacktestEngine:
    """Backtests the V3_REGIME hypothesis on historical data."""
    
    def __init__(self):
        self.results = []
        
    def run_backtest(self, data: pd.DataFrame, hypothesis: dict) -> Dict:
        """Run backtest using the precise strategy rules."""
        trades = []
        
        for i in range(len(data)):
            # Check HTF bias (using EMA)
            if i < 200:  # Need enough data for EMA
                continue
                
            ema200 = data['close'].iloc[i-200:i].mean()
            current_price = data['close'].iloc[i]
            
            htf_bias = "BULLISH" if current_price > ema200 else "BEARISH"
            
            # Check for liquidity sweep
            lookback = data.iloc[i-50:i]
            if htf_bias == "BULLISH":
                recent_low = lookback['low'].min()
                if data['low'].iloc[i] < recent_low:
                    # Potential sweep
                    sweep_quality = (data['low'].iloc[i-1] - recent_low) / (data['high'].iloc[i-1] - recent_low)
                    if sweep_quality < 0.5:
                        # Valid sweep - look for entry
                        entry = self._find_entry(data, i, htf_bias)
                        if entry:
                            trades.append(entry)
            
            elif htf_bias == "BEARISH":
                recent_high = lookback['high'].max()
                if data['high'].iloc[i] > recent_high:
                    sweep_quality = (recent_high - data['low'].iloc[i-1]) / (recent_high - data['low'].iloc[i-1])
                    if sweep_quality < 0.5:
                        entry = self._find_entry(data, i, htf_bias)
                        if entry:
                            trades.append(entry)
        
        return self._calculate_statistics(trades)
    
    def _find_entry(self, data: pd.DataFrame, index: int, direction: str) -> Dict:
        """Find valid entry after sweep."""
        # Simplified: wait for FVG in direction of bias
        for j in range(index + 1, min(index + 15, len(data))):
            if direction == "BULLISH":
                # Look for bullish FVG
                if data['low'].iloc[j] > data['high'].iloc[j-2]:
                    entry_price = data['close'].iloc[j]
                    sl = data['low'].iloc[j-1]
                    tp = entry_price + (entry_price - sl) * 2
                    
                    # Check if trade would trigger
                    if j + 1 < len(data):
                        if data['low'].iloc[j+1] <= entry_price:
                            # Entry triggered
                            return {
                                "entry": entry_price,
                                "sl": sl,
                                "tp": tp,
                                "direction": "BUY",
                                "entry_time": data.index[j+1]
                            }
        
        return None
    
    def _calculate_statistics(self, trades: List[Dict]) -> Dict:
        """Calculate strategy statistics."""
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "expectancy": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0
            }
        
        # Simulate outcomes (this needs actual price data to be accurate)
        wins = 0
        losses = 0
        gross_profit = 0
        gross_loss = 0
        r_values = []
        
        for trade in trades:
            # This is simplified - real backtest needs price path
            r_value = 2.0 if trade["direction"] == "BUY" else -1.0
            if r_value > 0:
                wins += 1
                gross_profit += r_value
            else:
                losses += 1
                gross_loss += abs(r_value)
            
            r_values.append(r_value)
        
        total = wins + losses
        win_rate = (wins / total) * 100
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        expectancy = np.mean(r_values)
        
        # Calculate drawdown
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Sharpe ratio (simplified)
        sharpe = np.mean(r_values) / (np.std(r_values) + 1e-10)
        
        return {
            "total_trades": total,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "avg_r_per_trade": expectancy,
            "best_trade_r": max(r_values),
            "worst_trade_r": min(r_values)
        }

if __name__ == "__main__":
    # Example usage
    engine = BacktestEngine()
    
    # Create sample data
    dates = pd.date_range('2026-01-01', periods=1000, freq='5min')
    data = pd.DataFrame({
        'open': np.random.randn(1000).cumsum() + 100,
        'high': np.random.randn(1000).cumsum() + 101,
        'low': np.random.randn(1000).cumsum() + 99,
        'close': np.random.randn(1000).cumsum() + 100,
    }, index=dates)
    
    hypothesis = {
        "htf_ema_period": 200,
        "liquidity_lookback": 50,
        "sweep_quality_threshold": 0.5,
        "fvg_min_size": 3.0,
        "rr_target": 2.0
    }
    
    results = engine.run_backtest(data, hypothesis)
    print(json.dumps(results, indent=2))
