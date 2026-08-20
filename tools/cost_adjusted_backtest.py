"""BACKTEST WITH REALISTIC TRANSACTION COSTS."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from datetime import datetime
import json

class CostAdjustedBacktest:
    """Backtest with realistic transaction costs."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
        # Transaction costs (from real Exness data)
        self.costs = {
            "spread_pips": 1.2,        # Average spread in pips
            "commission_per_lot": 3.5, # Commission per lot (if applicable)
            "slippage_pips": 1.5,      # Expected slippage in pips
            "min_lot": 0.01,
            "lot_step": 0.01,
            "stop_level_pips": 3.0,    # Minimum stop distance
            "freeze_level_pips": 1.0   # Freeze level
        }
        
        # Historical execution data (from ID 163 and other evidence)
        self.execution_history = {
            "typical_slippage": 0.8,   # Typical execution deviation
            "worst_slippage": 41.9,    # ID 163 extreme case
            "requote_rate": 0.05,      # 5% of orders requoted
            "partial_fill_rate": 0.02, # 2% partial fills
        }
        
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
        
        return df
    
    def apply_transaction_costs(self, trade, direction):
        """Apply realistic transaction costs to a trade."""
        # Spread cost (entry + exit)
        spread_cost = self.costs["spread_pips"] * 0.001  # Convert to price
        
        # Slippage
        slippage = np.random.normal(
            self.execution_history["typical_slippage"],
            self.execution_history["typical_slippage"] * 0.5
        )
        slippage = max(0, slippage)  # Slippage is always against you
        slippage_cost = slippage * 0.001
        
        # Commission (if applicable)
        # For micro accounts, commission is usually $0.35 per 0.01 lots
        commission_cost = 0.35  # $0.35 per trade
        
        # Total cost in price terms
        total_cost = spread_cost + slippage_cost
        
        if direction == "BUY":
            # For buys: entry higher, exit lower
            effective_entry = trade["entry"] + spread_cost + slippage_cost
            effective_sl = trade["sl"] + slippage_cost
            effective_tp = trade["tp"] - spread_cost
        else:
            # For sells: entry lower, exit higher
            effective_entry = trade["entry"] - spread_cost - slippage_cost
            effective_sl = trade["sl"] - slippage_cost
            effective_tp = trade["tp"] + spread_cost
        
        # Check if stop level is respected
        stop_distance = abs(effective_entry - effective_sl) / 0.001
        if stop_distance < self.costs["stop_level_pips"]:
            return None  # Stop too close, trade invalid
        
        return {
            "entry": effective_entry,
            "sl": effective_sl,
            "tp": effective_tp,
            "costs": {
                "spread_cost": spread_cost,
                "slippage_cost": slippage_cost,
                "commission_cost": commission_cost,
                "total_cost": total_cost
            }
        }
    
    def run_cost_adjusted_backtest(self):
        """Run backtest with realistic costs."""
        print("="*60)
        print("  BACKTEST WITH REALISTIC COSTS")
        print("="*60)
        
        # Load data
        data = self.load_data()
        if data is None:
            return None
        
        data = self.calculate_indicators(data)
        
        print(f"\nTransaction Costs:")
        print(f"  Spread: {self.costs['spread_pips']} pips")
        print(f"  Typical slippage: {self.execution_history['typical_slippage']} pips")
        print(f"  Commission: $0.35 per trade")
        print(f"  Stop level: {self.costs['stop_level_pips']} pips")
        
        # Run strategy with and without costs
        trades_no_costs = []
        trades_with_costs = []
        
        for i in range(200, len(data)):
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            bullish_bias = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
            
            if i >= 2:
                if bullish_bias and data['high'].iloc[i-2] < data['low'].iloc[i]:
                    direction = "BUY"
                    entry = data['close'].iloc[i]
                    sl = entry - (data['atr'].iloc[i] * 2.0)
                    tp = entry + (data['atr'].iloc[i] * 5.0)
                    
                    # Trade without costs
                    trade_no_cost = {"entry": entry, "sl": sl, "tp": tp}
                    trades_no_costs.append(self.simulate_trade(data, i, trade_no_cost, direction))
                    
                    # Trade with costs
                    trade_with_cost = self.apply_transaction_costs(
                        {"entry": entry, "sl": sl, "tp": tp}, direction
                    )
                    if trade_with_cost:
                        trades_with_costs.append(
                            self.simulate_trade(data, i, trade_with_cost, direction)
                        )
                
                elif not bullish_bias and data['low'].iloc[i-2] > data['high'].iloc[i]:
                    direction = "SELL"
                    entry = data['close'].iloc[i]
                    sl = entry + (data['atr'].iloc[i] * 2.0)
                    tp = entry - (data['atr'].iloc[i] * 5.0)
                    
                    trade_no_cost = {"entry": entry, "sl": sl, "tp": tp}
                    trades_no_costs.append(self.simulate_trade(data, i, trade_no_cost, direction))
                    
                    trade_with_cost = self.apply_transaction_costs(
                        {"entry": entry, "sl": sl, "tp": tp}, direction
                    )
                    if trade_with_cost:
                        trades_with_costs.append(
                            self.simulate_trade(data, i, trade_with_cost, direction)
                        )
        
        # Compare results
        print(f"\n{'='*60}")
        print("  RESULTS COMPARISON")
        print("="*60)
        
        stats_no_costs = self.calculate_stats(trades_no_costs)
        stats_with_costs = self.calculate_stats(trades_with_costs)
        
        print(f"\nWithout Costs:")
        print(f"  Trades: {stats_no_costs['trades']}")
        print(f"  Win rate: {stats_no_costs['win_rate']*100:.1f}%")
        print(f"  PF: {stats_no_costs['pf']:.3f}")
        print(f"  Expectancy: {stats_no_costs['expectancy']:.3f}R")
        print(f"  Total R: {stats_no_costs['total_r']:.1f}")
        
        print(f"\nWith Costs:")
        print(f"  Trades: {stats_with_costs['trades']}")
        print(f"  Win rate: {stats_with_costs['win_rate']*100:.1f}%")
        print(f"  PF: {stats_with_costs['pf']:.3f}")
        print(f"  Expectancy: {stats_with_costs['expectancy']:.3f}R")
        print(f"  Total R: {stats_with_costs['total_r']:.1f}")
        
        # Cost impact
        if stats_no_costs['trades'] > 0 and stats_with_costs['trades'] > 0:
            cost_impact = stats_no_costs['expectancy'] - stats_with_costs['expectancy']
            print(f"\nCost Impact:")
            print(f"  Expectancy reduction: {cost_impact:.3f}R")
            print(f"  % of edge lost: {(cost_impact / stats_no_costs['expectancy']) * 100:.1f}%")
        
        return {
            "no_costs": stats_no_costs,
            "with_costs": stats_with_costs
        }
    
    def simulate_trade(self, data, entry_idx, trade, direction):
        """Simulate trade with entry, SL, TP."""
        exit_idx = min(entry_idx + 50, len(data) - 1)
        
        for j in range(entry_idx + 1, exit_idx):
            if direction == "BUY":
                if data['low'].iloc[j] <= trade["sl"]:
                    # Stop loss hit
                    r = -1
                    return {"r": r, "result": "SL"}
                elif data['high'].iloc[j] >= trade["tp"]:
                    # Take profit hit
                    r = 2.5
                    return {"r": r, "result": "TP"}
            else:  # SELL
                if data['high'].iloc[j] >= trade["sl"]:
                    r = -1
                    return {"r": r, "result": "SL"}
                elif data['low'].iloc[j] <= trade["tp"]:
                    r = 2.5
                    return {"r": r, "result": "TP"}
        
        # Timeout
        exit_price = data['close'].iloc[exit_idx]
        if direction == "BUY":
            r = (exit_price - trade["entry"]) / (trade["entry"] - trade["sl"])
        else:
            r = (trade["entry"] - exit_price) / (trade["sl"] - trade["entry"])
        
        return {"r": r, "result": "TIMEOUT"}
    
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

if __name__ == "__main__":
    tester = CostAdjustedBacktest()
    results = tester.run_cost_adjusted_backtest()
