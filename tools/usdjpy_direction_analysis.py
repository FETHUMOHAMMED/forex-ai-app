"""USDJPY DIRECTION ANALYSIS - What makes it profitable?"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
import json
from pathlib import Path

class USDJPYDirectionAnalyzer:
    """Analyzes why USDJPY strategy works."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
    def load_and_analyze(self):
        """Load data and analyze by direction."""
        print("="*70)
        print("  USDJPY DIRECTION ANALYSIS")
        print("  Understanding WHY the strategy works")
        print("="*70)
        
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
        
        # Run strategy and separate by direction
        buy_trades = []
        sell_trades = []
        
        for i in range(200, len(data)):
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            # BUY trades (bullish bias)
            if data['ema_50'].iloc[i] > data['ema_200'].iloc[i]:
                if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry - (data['atr'].iloc[i] * 2.0)
                    tp = entry + (data['atr'].iloc[i] * 5.0)
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['low'].iloc[j] <= sl:
                            buy_trades.append({
                                "r": -1, 
                                "year": data['timestamp'].iloc[i].year,
                                "month": data['timestamp'].iloc[i].month
                            })
                            break
                        elif data['high'].iloc[j] >= tp:
                            buy_trades.append({
                                "r": 2.5,
                                "year": data['timestamp'].iloc[i].year,
                                "month": data['timestamp'].iloc[i].month
                            })
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (exit_price - entry) / (entry - sl)
                        buy_trades.append({
                            "r": r,
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
            
            # SELL trades (bearish bias)
            elif data['ema_50'].iloc[i] < data['ema_200'].iloc[i]:
                if i >= 2 and data['low'].iloc[i-2] > data['high'].iloc[i]:
                    entry = data['close'].iloc[i]
                    sl = entry + (data['atr'].iloc[i] * 2.0)
                    tp = entry - (data['atr'].iloc[i] * 5.0)
                    
                    exit_idx = min(i + 50, len(data) - 1)
                    
                    for j in range(i+1, exit_idx):
                        if data['high'].iloc[j] >= sl:
                            sell_trades.append({
                                "r": -1,
                                "year": data['timestamp'].iloc[i].year,
                                "month": data['timestamp'].iloc[i].month
                            })
                            break
                        elif data['low'].iloc[j] <= tp:
                            sell_trades.append({
                                "r": 2.5,
                                "year": data['timestamp'].iloc[i].year,
                                "month": data['timestamp'].iloc[i].month
                            })
                            break
                    else:
                        exit_price = data['close'].iloc[exit_idx]
                        r = (entry - exit_price) / (sl - entry)
                        sell_trades.append({
                            "r": r,
                            "year": data['timestamp'].iloc[i].year,
                            "month": data['timestamp'].iloc[i].month
                        })
        
        # Analyze BUY trades
        print(f"\n{'='*70}")
        print("  BUY TRADES (Bullish Bias)")
        print("="*70)
        buy_stats = self.analyze_trades(buy_trades, "BUY")
        
        # Analyze SELL trades
        print(f"\n{'='*70}")
        print("  SELL TRADES (Bearish Bias)")
        print("="*70)
        sell_stats = self.analyze_trades(sell_trades, "SELL")
        
        # Comparison
        print(f"\n{'='*70}")
        print("  BUY VS SELL COMPARISON")
        print("="*70)
        
        print(f"\n  {'Metric':20s} {'BUY':>12s} {'SELL':>12s} {'Difference':>12s}")
        print(f"  " + "-"*60)
        
        metrics = [
            ("Trades", buy_stats.get("trades", 0), sell_stats.get("trades", 0)),
            ("Win Rate", buy_stats.get("win_rate", 0), sell_stats.get("win_rate", 0)),
            ("Profit Factor", buy_stats.get("pf", 0), sell_stats.get("pf", 0)),
            ("Expectancy", buy_stats.get("expectancy", 0), sell_stats.get("expectancy", 0)),
            ("Total R", buy_stats.get("total_r", 0), sell_stats.get("total_r", 0)),
            ("Max Drawdown", buy_stats.get("max_dd", 0), sell_stats.get("max_dd", 0)),
        ]
        
        for name, buy_val, sell_val in metrics:
            if isinstance(buy_val, float):
                diff = buy_val - sell_val
                print(f"  {name:20s} {buy_val:12.3f} {sell_val:12.3f} {diff:+12.3f}")
            else:
                diff = buy_val - sell_val
                print(f"  {name:20s} {buy_val:12d} {sell_val:12d} {diff:+12d}")
        
        # Key insights
        print(f"\n{'='*70}")
        print("  KEY INSIGHTS")
        print("="*70)
        
        if buy_stats.get("expectancy", 0) > sell_stats.get("expectancy", 0):
            print(f"\n  BUY trades are MORE profitable")
            print(f"  BUY expectancy: {buy_stats.get('expectancy', 0):.3f}R")
            print(f"  SELL expectancy: {sell_stats.get('expectancy', 0):.3f}R")
            print(f"  Difference: {buy_stats.get('expectancy', 0) - sell_stats.get('expectancy', 0):.3f}R")
        else:
            print(f"\n  SELL trades are MORE profitable")
            print(f"  SELL expectancy: {sell_stats.get('expectancy', 0):.3f}R")
            print(f"  BUY expectancy: {buy_stats.get('expectancy', 0):.3f}R")
        
        # Yearly breakdown by direction
        print(f"\n{'='*70}")
        print("  YEARLY BREAKDOWN BY DIRECTION")
        print("="*70)
        
        buy_df = pd.DataFrame(buy_trades) if buy_trades else pd.DataFrame()
        sell_df = pd.DataFrame(sell_trades) if sell_trades else pd.DataFrame()
        
        all_years = sorted(set(
            (buy_df['year'].tolist() if not buy_df.empty else []) +
            (sell_df['year'].tolist() if not sell_df.empty else [])
        ))
        
        print(f"\n  Year    BUY R     SELL R    Combined")
        print(f"  " + "-"*50)
        
        for year in all_years:
            buy_r = buy_df[buy_df['year'] == year]['r'].sum() if not buy_df.empty and year in buy_df['year'].values else 0
            sell_r = sell_df[sell_df['year'] == year]['r'].sum() if not sell_df.empty and year in sell_df['year'].values else 0
            combined = buy_r + sell_r
            
            print(f"  {year}    {buy_r:+.1f}     {sell_r:+.1f}      {combined:+.1f}")
        
        return {
            "buy": buy_stats,
            "sell": sell_stats,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades
        }
    
    def analyze_trades(self, trades, direction):
        """Analyze trades for a direction."""
        if not trades:
            print(f"  No {direction} trades found")
            return {"trades": 0}
        
        r_values = [t["r"] for t in trades]
        wins = sum(1 for r in r_values if r > 0)
        losses = sum(1 for r in r_values if r < 0)
        win_rate = wins / len(r_values)
        
        gross_profit = sum(r for r in r_values if r > 0)
        gross_loss = abs(sum(r for r in r_values if r < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        expectancy = np.mean(r_values)
        total_r = sum(r_values)
        
        # Drawdown
        cumulative = np.cumsum(r_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_dd = np.min(drawdown) if len(drawdown) > 0 else 0
        
        # Statistical significance
        t_stat, p_value = scipy_stats.ttest_1samp(r_values, 0)
        
        print(f"\n  Trades: {len(r_values)}")
        print(f"  Wins: {wins}, Losses: {losses}")
        print(f"  Win rate: {win_rate*100:.1f}%")
        print(f"  Profit factor: {pf:.3f}")
        print(f"  Expectancy: {expectancy:.3f}R")
        print(f"  Total R: {total_r:.1f}")
        print(f"  Max drawdown: {max_dd:.1f}R")
        print(f"  T-statistic: {t_stat:.3f}")
        print(f"  P-value: {p_value:.4f}")
        print(f"  Significant: {'YES' if p_value < 0.05 else 'NO'}")
        
        return {
            "trades": len(r_values),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "pf": pf,
            "expectancy": expectancy,
            "total_r": total_r,
            "max_dd": max_dd,
            "t_stat": t_stat,
            "p_value": p_value
        }

if __name__ == "__main__":
    analyzer = USDJPYDirectionAnalyzer()
    results = analyzer.load_and_analyze()
