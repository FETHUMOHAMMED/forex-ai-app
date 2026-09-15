"""AUTHORITATIVE BASELINE - Complete V4 statistics."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.strategy.canonical_v4 import CanonicalV4Strategy

class AuthoritativeBaseline:
    """One complete, authoritative V4 baseline."""
    
    def __init__(self):
        self.strategy = CanonicalV4Strategy()
        
    def generate_baseline(self):
        """Generate complete baseline with ALL statistics."""
        print("="*70)
        print("  AUTHORITATIVE V4 BASELINE")
        print("="*70)
        
        # Load and prepare data
        data = self.strategy.load_data(bars=10000)
        data = self.strategy.generate_features(data)
        
        # Strategy definition
        print(f"\n  STRATEGY DEFINITION:")
        print(f"    Version: {self.strategy.strategy_version}")
        print(f"    Period: {data['timestamp'].min()} to {data['timestamp'].max()}")
        print(f"    Symbol: {self.strategy.PARAMS['pair']}")
        print(f"    Direction: {self.strategy.PARAMS['direction']}")
        print(f"    Session: {self.strategy.PARAMS['sessions']}")
        print(f"    Risk: {self.strategy.PARAMS['risk_percent']}%")
        print(f"    SL: {self.strategy.PARAMS['sl_atr_mult']}x ATR")
        print(f"    TP: {self.strategy.PARAMS['sl_atr_mult'] * self.strategy.PARAMS['rr_ratio']}x ATR")
        print(f"    Entry: next-bar open (simulated)")
        
        # Run strategy
        trades = []
        for i in range(200, len(data)):
            if data['signal'].iloc[i]:
                trade = self.strategy.simulate_trade(data, i)
                trade['entry_time'] = data['timestamp'].iloc[i]
                trade['year'] = data['timestamp'].iloc[i].year
                trade['month'] = data['timestamp'].iloc[i].month
                trades.append(trade)
        
        if not trades:
            print("\n  No trades generated")
            return None
        
        r_values = [t['r'] for t in trades]
        wins = [r for r in r_values if r > 0]
        losses = [r for r in r_values if r < 0]
        
        # Calculate drawdown
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_dd = np.max(drawdown)
        
        # Consecutive losses
        max_consec_loss = 0
        cur_loss = 0
        for r in r_values:
            if r < 0:
                cur_loss += 1
                max_consec_loss = max(max_consec_loss, cur_loss)
            else:
                cur_loss = 0
        
        # Trade duration
        durations = [t.get('bars_held', 0) for t in trades]
        avg_duration_bars = np.mean(durations)
        avg_duration_hours = avg_duration_bars * 4  # H4 bars
        
        # Complete statistics
        baseline = {
            "trades": len(r_values),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(r_values),
            "profit_factor": sum(wins) / abs(sum(losses)) if losses else float('inf'),
            "expectancy_r": np.mean(r_values),
            "total_r": sum(r_values),
            "max_drawdown_r": max_dd,
            "average_win_r": np.mean(wins) if wins else 0,
            "average_loss_r": np.mean(losses) if losses else 0,
            "largest_win_r": max(r_values),
            "largest_loss_r": min(r_values),
            "max_consecutive_losses": max_consec_loss,
            "avg_duration_hours": avg_duration_hours,
            "sharpe_ratio": np.mean(r_values) / np.std(r_values) if np.std(r_values) > 0 else 0
        }
        
        # Display complete baseline
        print(f"\n{'='*70}")
        print("  COMPLETE BASELINE STATISTICS")
        print("="*70)
        
        print(f"\n  TRADE COUNT:")
        print(f"    Total: {baseline['trades']}")
        print(f"    Wins: {baseline['wins']}")
        print(f"    Losses: {baseline['losses']}")
        
        print(f"\n  PERFORMANCE:")
        print(f"    Win rate: {baseline['win_rate']*100:.1f}%")
        print(f"    Profit factor: {baseline['profit_factor']:.3f}")
        print(f"    Expectancy: {baseline['expectancy_r']:.3f}R")
        print(f"    Total R: {baseline['total_r']:.1f}")
        
        print(f"\n  RISK METRICS:")
        print(f"    Max drawdown: {baseline['max_drawdown_r']:.1f}R")
        print(f"    Sharpe ratio: {baseline['sharpe_ratio']:.3f}")
        print(f"    Max consecutive losses: {baseline['max_consecutive_losses']}")
        
        print(f"\n  TRADE QUALITY:")
        print(f"    Average win: +{baseline['average_win_r']:.2f}R")
        print(f"    Average loss: {baseline['average_loss_r']:.2f}R")
        print(f"    Largest win: +{baseline['largest_win_r']:.2f}R")
        print(f"    Largest loss: {baseline['largest_loss_r']:.2f}R")
        print(f"    Avg duration: {baseline['avg_duration_hours']:.1f} hours")
        
        # Yearly distribution
        print(f"\n  YEARLY DISTRIBUTION:")
        trades_df = pd.DataFrame(trades)
        yearly = trades_df.groupby('year')['r'].agg(['sum', 'count'])
        for year, row in yearly.iterrows():
            print(f"    {year}: {row['sum']:+.1f}R in {row['count']} trades")
        
        # Monthly distribution
        print(f"\n  MONTHLY DISTRIBUTION:")
        trades_df['month_key'] = trades_df['year'].astype(str) + '-' + trades_df['month'].astype(str).str.zfill(2)
        monthly = trades_df.groupby('month_key')['r'].agg(['sum', 'count'])
        profitable_months = (monthly['sum'] > 0).sum()
        print(f"    Profitable months: {profitable_months}/{len(monthly)}")
        
        print(f"\n{'='*70}")
        print("  BASELINE COMPLETE")
        print("="*70)
        
        return baseline

if __name__ == "__main__":
    baseline = AuthoritativeBaseline()
    results = baseline.generate_baseline()
