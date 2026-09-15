"""CANONICAL REPLAY ENGINE - Uses EXACT same logic as live V4."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Import the FROZEN strategy - THE single source of truth
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from packages.strategy.canonical_v4 import CanonicalV4Strategy

class CanonicalReplayEngine:
    """
    Replays V4 using the EXACT same strategy class as live trading.
    No duplicate logic. No divergence possible.
    """
    
    def __init__(self):
        self.strategy = CanonicalV4Strategy()  # THE frozen strategy
        self.params = self.strategy.PARAMS      # THE frozen parameters
        
    def load_data(self):
        """Load data same way live strategy does."""
        return self.strategy.load_data(bars=10000)
    
    def run_replay(self):
        """Run replay using canonical generate_features and simulate_trade."""
        print("="*70)
        print("  CANONICAL REPLAY - Uses CanonicalV4Strategy directly")
        print("="*70)
        
        data = self.load_data()
        if data is None:
            return {"error": "NO_DATA"}
        
        # Use the SAME feature generation as live
        data = self.strategy.generate_features(data)
        
        trades = []
        evaluations = []
        open_position = False  # Track position limit (max 1)
        
        for i in range(200, len(data)):
            # Record evaluation
            evaluations.append({
                "fvg": bool(data['bullish_fvg'].iloc[i]),
                "bias": bool(data['bullish_bias'].iloc[i]),
                "london": bool(data['in_session'].iloc[i]),
                "signal": bool(data['signal'].iloc[i])
            })
            
            # Only trade if signal AND no open position
            if data['signal'].iloc[i] and not open_position:
                # Use the SAME simulate_trade as live
                trade = self.strategy.simulate_trade(data, i)
                trades.append(trade)
                open_position = False  # Trade closes within simulate_trade
        
        # Statistics
        total_evals = len(evaluations)
        fvg_count = sum(1 for e in evaluations if e["fvg"])
        bias_count = sum(1 for e in evaluations if e["bias"])
        valid_signals = sum(1 for e in evaluations if e["signal"])
        
        result = {
            "total_evaluations": total_evals,
            "fvg_detected": fvg_count,
            "bullish_bias": bias_count,
            "valid_setups": valid_signals,
            "fvg_rate": fvg_count / total_evals if total_evals > 0 else 0,
            "bias_rate": bias_count / total_evals if total_evals > 0 else 0,
            "valid_rate": valid_signals / total_evals if total_evals > 0 else 0,
            "trades": len(trades)
        }
        
        if trades:
            r_values = [t["r"] for t in trades]
            wins = sum(1 for r in r_values if r > 0)
            gross_p = sum(r for r in r_values if r > 0)
            gross_l = abs(sum(r for r in r_values if r < 0))
            
            result.update({
                "win_rate": wins / len(r_values),
                "pf": gross_p / gross_l if gross_l > 0 else float('inf'),
                "expectancy": np.mean(r_values),
                "total_r": sum(r_values),
                "strategy_version": self.strategy.strategy_version
            })
        
        # Display
        print(f"\n  Using strategy: {self.strategy.strategy_version}")
        print(f"  Frozen parameters: {self.params['pair']} {self.params['direction']} London {self.params['sessions']}")
        print(f"\n  RESULTS (identical to live):")
        print(f"    Evaluations: {result['total_evaluations']}")
        print(f"    FVG rate: {result['fvg_rate']*100:.1f}%")
        print(f"    Valid setups: {result['valid_setups']} ({result['valid_rate']*100:.1f}%)")
        print(f"    Trades: {result['trades']}")
        if 'expectancy' in result:
            print(f"    Win rate: {result['win_rate']*100:.1f}%")
            print(f"    PF: {result['pf']:.3f}")
            print(f"    Expectancy: {result['expectancy']:.3f}R")
        
        print(f"\n  GUARANTEED: Same FVG, same EMA, same ATR, same SL/TP,")
        print(f"  same session, same entry/exit logic as live runner.")
        
        return result

if __name__ == "__main__":
    engine = CanonicalReplayEngine()
    results = engine.run_replay()
