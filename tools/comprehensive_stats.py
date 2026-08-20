# -*- coding: utf-8 -*-
"""COMPREHENSIVE STRATEGY STATISTICS ANALYZER."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
import json
from datetime import datetime

class ComprehensiveStatsAnalyzer:
    """Calculates all meaningful strategy statistics."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
    def load_and_run_strategy(self):
        """Load data and run strategy."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        if rates is None:
            return None
        
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
            
            bullish_bias = data['ema_50'].iloc[i] > data['ema_200'].iloc[i]
            
            if i >= 2:
                if bullish_bias and data['high'].iloc[i-2] < data['low'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry - (data['atr'].iloc[i] * 2.0)
                    tp = entry + (data['atr'].iloc[i] * 5.0)
                    
                    # Apply typical costs
                    entry_actual = entry + (1.2 * 0.001) + (0.8 * 0.001)
                    sl_actual = sl + (0.8 * 0.001)
                    tp_actual = tp - (1.2 * 0.001)
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['low'].iloc[j] <= sl_actual:
                            trades.append({
                                "r": -1.035,  # -1R minus commission
                                "result": "SL",
                                "entry_time": data['timestamp'].iloc[i],
                                "exit_time": data['timestamp'].iloc[j],
                                "direction": "BUY",
                                "bars_held": j - i,
                                "year": data['timestamp'].iloc[i].year,
                                "month": data['timestamp'].iloc[i].month
                            })
                            break
                        elif data['high'].iloc[j] >= tp_actual:
                            trades.append({
                                "r": 2.465,  # 2.5R minus commission
                                "result": "TP",
                                "entry_time": data['timestamp'].iloc[i],
                                "exit_time": data['timestamp'].iloc[j],
                                "direction": "BUY",
                                "bars_held": j - i,
                                "year": data['timestamp'].iloc[i].year,
                                "month": data['timestamp'].iloc[i].month
                            })
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (exit_price - entry_actual) / (entry_actual - sl_actual)
                        trades.append({
                            "r": r - 0.035,
                            "result": "TIMEOUT",
                            "entry_time": data['timestamp'].iloc[i],
                            "exit_time": data['timestamp'].iloc[exit_idx],
                            "direction": "BUY",
                            "bars_held": 50,
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
                
                elif not bullish_bias and data['low'].iloc[i-2] > data['high'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry + (data['atr'].iloc[i] * 2.0)
                    tp = entry - (data['atr'].iloc[i] * 5.0)
                    
                    entry_actual = entry - (1.2 * 0.001) - (0.8 * 0.001)
                    sl_actual = sl - (0.8 * 0.001)
                    tp_actual = tp + (1.2 * 0.001)
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['high'].iloc[j] >= sl_actual:
                            trades.append({
                                "r": -1.035,
                                "result": "SL",
                                "entry_time": data['timestamp'].iloc[i],
                                "exit_time": data['timestamp'].iloc[j],
                                "direction": "SELL",
                                "bars_held": j - i,
                                "year": data['timestamp'].iloc[i].year,
                                "month": data['timestamp'].iloc[i].month
                            })
                            break
                        elif data['low'].iloc[j] <= tp_actual:
                            trades.append({
                                "r": 2.465,
                                "result": "TP",
                                "entry_time": data['timestamp'].iloc[i],
                                "exit_time": data['timestamp'].iloc[j],
                                "direction": "SELL",
                                "bars_held": j - i,
                                "year": data['timestamp'].iloc[i].year,
                                "month": data['timestamp'].iloc[i].month
                            })
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (entry_actual - exit_price) / (sl_actual - entry_actual)
                        trades.append({
                            "r": r - 0.035,
                            "result": "TIMEOUT",
                            "entry_time": data['timestamp'].iloc[i],
                            "exit_time": data['timestamp'].iloc[exit_idx],
                            "direction": "SELL",
                            "bars_held": 50,
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
        
        return trades
    
    def calculate_comprehensive_stats(self, trades):
        """Calculate all meaningful statistics."""
        if not trades:
            return {}
        
        trades_df = pd.DataFrame(trades)
        r_values = trades_df['r'].values
        
        # Basic statistics
        total_trades = len(r_values)
        wins = r_values[r_values > 0]
        losses = r_values[r_values < 0]
        
        win_rate = len(wins) / total_trades
        loss_rate = len(losses) / total_trades
        avg_win = np.mean(wins) if len(wins) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Expectancy (simplified formula)
        expectancy_simple = (win_rate * avg_win) - (loss_rate * abs(avg_loss))
        expectancy_actual = np.mean(r_values)
        
        # Risk metrics
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_drawdown = np.min(drawdown)
        
        # Recovery factor
        recovery_factor = cumulative[-1] / abs(max_drawdown) if max_drawdown < 0 else float('inf')
        
        # Sharpe ratio
        sharpe = np.mean(r_values) / np.std(r_values) if np.std(r_values) > 0 else 0
        
        # Sortino ratio (downside deviation only)
        downside_returns = r_values[r_values < 0]
        downside_deviation = np.std(downside_returns) if len(downside_returns) > 0 else 0
        sortino = np.mean(r_values) / downside_deviation if downside_deviation > 0 else 0
        
        # R-multiple distribution
        r_percentiles = {
            "p5": np.percentile(r_values, 5),
            "p25": np.percentile(r_values, 25),
            "p50": np.percentile(r_values, 50),
            "p75": np.percentile(r_values, 75),
            "p95": np.percentile(r_values, 95)
        }
        
        # Worst losing streak
        max_consecutive_losses = 0
        current_losses = 0
        for r in r_values:
            if r < 0:
                current_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_losses = 0
        
        # Average holding time
        avg_bars_held = trades_df['bars_held'].mean()
        avg_holding_hours = avg_bars_held * 4  # H4 bars
        
        # Monthly performance
        trades_df['month_key'] = trades_df['year'].astype(str) + '-' + trades_df['month'].astype(str).str.zfill(2)
        monthly = trades_df.groupby('month_key')['r'].agg(['sum', 'count', 'mean'])
        
        best_month = monthly.loc[monthly['sum'].idxmax()]
        worst_month = monthly.loc[monthly['sum'].idxmin()]
        
        # Direction analysis
        long_trades = trades_df[trades_df['direction'] == 'BUY']
        short_trades = trades_df[trades_df['direction'] == 'SELL']
        
        long_stats = {
            "trades": len(long_trades),
            "win_rate": (long_trades['r'] > 0).mean() if len(long_trades) > 0 else 0,
            "expectancy": long_trades['r'].mean() if len(long_trades) > 0 else 0
        }
        
        short_stats = {
            "trades": len(short_trades),
            "win_rate": (short_trades['r'] > 0).mean() if len(short_trades) > 0 else 0,
            "expectancy": short_trades['r'].mean() if len(short_trades) > 0 else 0
        }
        
        return {
            "basic": {
                "total_trades": total_trades,
                "win_rate": win_rate,
                "loss_rate": loss_rate,
                "avg_win_r": avg_win,
                "avg_loss_r": avg_loss,
                "profit_factor": profit_factor
            },
            "expectancy": {
                "simplified_formula": expectancy_simple,
                "actual_calculation": expectancy_actual
            },
            "risk": {
                "max_drawdown_r": max_drawdown,
                "recovery_factor": recovery_factor,
                "sharpe_ratio": sharpe,
                "sortino_ratio": sortino,
                "max_consecutive_losses": max_consecutive_losses
            },
            "distribution": {
                "r_percentiles": r_percentiles,
                "avg_holding_hours": avg_holding_hours,
                "best_month": best_month.to_dict(),
                "worst_month": worst_month.to_dict()
            },
            "direction": {
                "long": long_stats,
                "short": short_stats
            }
        }
    
    def run_full_analysis(self):
        """Run complete analysis."""
        print("="*70)
        print("  COMPREHENSIVE STRATEGY STATISTICS")
        print("  FVG_H4_2.5R_London (After Costs)")
        print("="*70)
        
        trades = self.load_and_run_strategy()
        if not trades:
            print("No trades generated")
            return None
        
        stats = self.calculate_comprehensive_stats(trades)
        
        # Print everything
        print(f"\n{'='*70}")
        print("  1. BASIC STATISTICS")
        print("="*70)
        b = stats["basic"]
        print(f"  Total trades: {b['total_trades']}")
        print(f"  Win rate: {b['win_rate']*100:.1f}%")
        print(f"  Loss rate: {b['loss_rate']*100:.1f}%")
        print(f"  Average win: +{b['avg_win_r']:.2f}R")
        print(f"  Average loss: {b['avg_loss_r']:.2f}R")
        print(f"  Profit factor: {b['profit_factor']:.3f}")
        
        print(f"\n{'='*70}")
        print("  2. EXPECTANCY ANALYSIS")
        print("="*70)
        e = stats["expectancy"]
        print(f"  Simplified formula: ({b['win_rate']*100:.1f}% x {b['avg_win_r']:.2f}) - ({b['loss_rate']*100:.1f}% x {abs(b['avg_loss_r']):.2f})")
        print(f"  = ({b['win_rate']*b['avg_win_r']:.3f}) - ({b['loss_rate']*abs(b['avg_loss_r']):.3f})")
        print(f"  = {e['simplified_formula']:.3f}R")
        print(f"  Actual calculated: {e['actual_calculation']:.3f}R")
        
        print(f"\n{'='*70}")
        print("  3. RISK METRICS")
        print("="*70)
        r = stats["risk"]
        print(f"  Max drawdown: {r['max_drawdown_r']:.1f}R")
        print(f"  Recovery factor: {r['recovery_factor']:.2f}")
        print(f"  Sharpe ratio: {r['sharpe_ratio']:.3f}")
        print(f"  Sortino ratio: {r['sortino_ratio']:.3f}")
        print(f"  Worst losing streak: {r['max_consecutive_losses']} trades")
        
        print(f"\n{'='*70}")
        print("  4. R-MULTIPLE DISTRIBUTION")
        print("="*70)
        d = stats["distribution"]
        print(f"  5th percentile: {d['r_percentiles']['p5']:.2f}R")
        print(f"  25th percentile: {d['r_percentiles']['p25']:.2f}R")
        print(f"  Median (50th): {d['r_percentiles']['p50']:.2f}R")
        print(f"  75th percentile: {d['r_percentiles']['p75']:.2f}R")
        print(f"  95th percentile: {d['r_percentiles']['p95']:.2f}R")
        print(f"  Average holding time: {d['avg_holding_hours']:.1f} hours ({d['avg_holding_hours']/24:.1f} days)")
        
        print(f"\n{'='*70}")
        print("  5. MONTHLY PERFORMANCE")
        print("="*70)
        print(f"  Best month: {d['best_month']['sum']:.1f}R in {d['best_month']['count']} trades")
        print(f"  Worst month: {d['worst_month']['sum']:.1f}R in {d['worst_month']['count']} trades")
        
        print(f"\n{'='*70}")
        print("  6. DIRECTION ANALYSIS")
        print("="*70)
        dir_stats = stats["direction"]
        print(f"  Long trades: {dir_stats['long']['trades']} ({dir_stats['long']['win_rate']*100:.1f}% win, {dir_stats['long']['expectancy']:.2f}R exp)")
        print(f"  Short trades: {dir_stats['short']['trades']} ({dir_stats['short']['win_rate']*100:.1f}% win, {dir_stats['short']['expectancy']:.2f}R exp)")
        
        # The advisor's example comparison
        print(f"\n{'='*70}")
        print("  7. EXPECTANCY FORMULA VALIDATION")
        print("="*70)
        print(f"  Our strategy:")
        print(f"    Win rate: {b['win_rate']*100:.1f}%")
        print(f"    Avg win: +{b['avg_win_r']:.2f}R")
        print(f"    Avg loss: {b['avg_loss_r']:.2f}R")
        print(f"    E = ({b['win_rate']*100:.1f}% x {b['avg_win_r']:.2f}) - ({b['loss_rate']*100:.1f}% x {abs(b['avg_loss_r']):.2f})")
        print(f"    E = +{e['simplified_formula']:.3f}R ?")
        
        print(f"\n  Counter-example (high win rate, bad R:R):")
        print(f"    Win rate: 70%")
        print(f"    Avg win: +0.5R")
        print(f"    Avg loss: -2R")
        print(f"    E = (70% x 0.5) - (30% x 2)")
        print(f"    E = -0.25R ? (loses money despite 70% win rate)")
        
        print(f"\n{'='*70}")
        print("  FINAL ASSESSMENT")
        print("="*70)
        
        # Quality criteria
        quality_checks = [
            (e['actual_calculation'] > 0.2, f"Expectancy > 0.2R: {e['actual_calculation']:.3f}R"),
            (b['profit_factor'] > 1.3, f"Profit factor > 1.3: {b['profit_factor']:.3f}"),
            (r['sharpe_ratio'] > 0.5, f"Sharpe > 0.5: {r['sharpe_ratio']:.3f}"),
            (r['sortino_ratio'] > 1.0, f"Sortino > 1.0: {r['sortino_ratio']:.3f}"),
            (r['recovery_factor'] > 2.0, f"Recovery factor > 2: {r['recovery_factor']:.2f}"),
            (b['total_trades'] > 100, f"Sample size > 100: {b['total_trades']}"),
            (abs(r['max_drawdown_r']) < 15, f"Max DD < 15R: {abs(r['max_drawdown_r']):.1f}R"),
        ]
        
        for passed, description in quality_checks:
            status = "?" if passed else "?"
            print(f"  {status} {description}")
        
        return stats

if __name__ == "__main__":
    analyzer = ComprehensiveStatsAnalyzer()
    stats = analyzer.run_full_analysis()

