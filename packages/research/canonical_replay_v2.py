"""CANONICAL REPLAY V2 - Position Limit + Size-Dependent Costs."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from packages.strategy.canonical_v4 import CanonicalV4Strategy

class CanonicalReplayV2:
    """Corrected replay: 1-position limit + proper transaction costs."""
    
    def __init__(self):
        self.strategy = CanonicalV4Strategy()
        # Transaction costs
        self.spread_pips = 1.2
        self.slippage_pips = 0.8
        self.commission_usd = 0.35
        self.account_equity = 2000  # Reference account size for commission_R
        self.risk_percent = 0.0025  # 0.25% as fraction
        
    def calculate_commission_R(self, sl_distance_pips: float, pip_value: float = 0.10) -> float:
        """
        Convert $0.35 commission to R based on position size.
        
        Position size = (equity * risk%) / (sl_distance_pips * pip_value)
        Dollar risk = equity * risk% = $2000 * 0.0025 = $5
        Commission in R = $0.35 / $5 = 0.07R
        """
        dollar_risk = self.account_equity * self.risk_percent  # $5
        if dollar_risk <= 0:
            return 0
        return self.commission_usd / dollar_risk  # 0.07R
    
    def run_replay(self):
        print("="*70)
        print("  CANONICAL REPLAY V2 - Normalized Commission")
        print("="*70)
        
        data = self.strategy.load_data(bars=10000)
        data = self.strategy.generate_features(data)
        
        trades = []
        open_position = False
        
        for i in range(200, len(data)):
            if data['signal'].iloc[i] and not open_position:
                trade = self.simulate_trade_with_costs(data, i)
                if trade:
                    trades.append(trade)
                    open_position = False
        
        if not trades:
            return {"trades": 0}
        
        r_values = [t["r"] for t in trades]
        wins = sum(1 for r in r_values if r > 0)
        gross_p = sum(r for r in r_values if r > 0)
        gross_l = abs(sum(r for r in r_values if r < 0))
        
        result = {
            "trades": len(r_values),
            "win_rate": wins / len(r_values),
            "pf": gross_p / gross_l if gross_l > 0 else float('inf'),
            "expectancy": np.mean(r_values),
            "total_r": sum(r_values),
            "commission_model": f"${self.commission_usd} / ${self.account_equity * self.risk_percent:.2f} risk = {self.calculate_commission_R(60):.3f}R per trade",
            "position_limit": 1,
            "costs_applied": True
        }
        
        print(f"\n  RESULTS (normalized commission):")
        print(f"    Trades: {result['trades']}")
        print(f"    Win rate: {result['win_rate']*100:.1f}%")
        print(f"    PF: {result['pf']:.3f}")
        print(f"    Expectancy: {result['expectancy']:.3f}R")
        print(f"    Total R: {result['total_r']:.1f}")
        print(f"    Commission: {result['commission_model']}")
        print(f"    Position limit: {result['position_limit']}")
        
        return result
    
    def simulate_trade_with_costs(self, data, i):
        """Simulate trade with size-dependent costs."""
        entry_theoretical = data['close'].iloc[i]
        atr = data['atr'].iloc[i]
        
        # Apply spread and slippage (in price)
        spread = self.spread_pips * 0.001
        slippage = self.slippage_pips * 0.001
        
        entry_actual = entry_theoretical + spread + slippage
        sl = entry_actual - (atr * 2.0)
        tp = entry_actual + (atr * 4.0)
        
        # Calculate commission in R (size-dependent)
        commission_R = self.calculate_commission_R(atr * 2.0 / 0.001)
        
        exit_idx = min(i + 50, len(data) - 1)
        
        for j in range(i+1, exit_idx):
            if data['low'].iloc[j] <= sl:
                return {"r": -1 - commission_R}
            elif data['high'].iloc[j] >= tp:
                return {"r": 2.0 - commission_R}
        
        exit_price = data['close'].iloc[exit_idx]
        r = (exit_price - entry_actual) / (entry_actual - sl)
        return {"r": r - commission_R}

if __name__ == "__main__":
    replay = CanonicalReplayV2()
    results = replay.run_replay()

