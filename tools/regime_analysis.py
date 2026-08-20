"""MARKET REGIME ANALYSIS - Does the strategy work in all conditions?"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
import json
from pathlib import Path

class RegimeAnalyzer:
    """Analyzes strategy performance across different market regimes."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
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
    
    def classify_regime(self, data):
        """Classify market into regimes."""
        df = data.copy()
        
        # Calculate indicators for regime classification
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        # ATR for volatility
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        df['atr_ma'] = df['atr'].rolling(50).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma']
        
        # Trend strength
        df['trend_strength'] = abs(df['ema_50'] - df['ema_200']) / df['ema_200']
        df['trend_strength_ma'] = df['trend_strength'].rolling(50).mean()
        
        # Hour for session filter
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        # Classify regimes
        df['regime'] = 'RANGE'
        
        # Trending up
        df.loc[(df['ema_50'] > df['ema_200']) & 
               (df['trend_strength'] > df['trend_strength_ma'] * 1.2), 'regime'] = 'TRENDING_UP'
        
        # Trending down
        df.loc[(df['ema_50'] < df['ema_200']) & 
               (df['trend_strength'] > df['trend_strength_ma'] * 1.2), 'regime'] = 'TRENDING_DOWN'
        
        # Breakout (high volatility)
        df.loc[df['atr_ratio'] > 1.5, 'regime'] = 'BREAKOUT'
        
        # High volatility
        df.loc[df['atr_ratio'] > 2.0, 'regime'] = 'HIGH_VOLATILITY'
        
        # Low volatility (quiet)
        df.loc[df['atr_ratio'] < 0.7, 'regime'] = 'LOW_VOLATILITY'
        
        return df
    
    def run_strategy_with_regime(self, data):
        """Run strategy and record regime for each trade."""
        trades = []
        
        for i in range(200, len(data)):
            if not (7 <= data['hour'].iloc[i] <= 11):
                continue
            
            # Long only
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            if i >= 2 and data['high'].iloc[i-2] < data['low'].iloc[i]:
                entry = data['close'].iloc[i]
                sl = entry - (data['atr'].iloc[i] * 2.0)
                tp = entry + (data['atr'].iloc[i] * 5.0)
                
                exit_idx = min(i + 50, len(data) - 1)
                
                for j in range(i+1, exit_idx):
                    if data['low'].iloc[j] <= sl:
                        trades.append({
                            "r": -1,
                            "regime": data['regime'].iloc[i],
                            "year": data['timestamp'].iloc[i].year
                        })
                        break
                    elif data['high'].iloc[j] >= tp:
                        trades.append({
                            "r": 2.5,
                            "regime": data['regime'].iloc[i],
                            "year": data['timestamp'].iloc[i].year
                        })
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    trades.append({
                        "r": r,
                        "regime": data['regime'].iloc[i],
                        "year": data['timestamp'].iloc[i].year
                    })
        
        return trades
    
    def analyze_regime_performance(self, trades):
        """Analyze performance by regime."""
        if not trades:
            return {}
        
        trades_df = pd.DataFrame(trades)
        
        print(f"\n{'='*70}")
        print("  STRATEGY PERFORMANCE BY MARKET REGIME")
        print("="*70)
        
        regimes = ['TRENDING_UP', 'TRENDING_DOWN', 'BREAKOUT', 'HIGH_VOLATILITY', 'LOW_VOLATILITY', 'RANGE']
        
        print(f"\n  Regime          Trades  WinRate  PF      Expectancy  Total R")
        print(f"  " + "-"*70)
        
        regime_stats = {}
        
        for regime in regimes:
            regime_trades = trades_df[trades_df['regime'] == regime]
            
            if len(regime_trades) == 0:
                print(f"  {regime:15s}      0     -      -         -          -")
                continue
            
            r_values = regime_trades['r'].values
            wins = (r_values > 0).sum()
            win_rate = wins / len(r_values)
            gross_profit = sum(r for r in r_values if r > 0)
            gross_loss = abs(sum(r for r in r_values if r < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            expectancy = np.mean(r_values)
            total_r = sum(r_values)
            
            regime_stats[regime] = {
                "trades": len(regime_trades),
                "win_rate": win_rate,
                "pf": pf,
                "expectancy": expectancy,
                "total_r": total_r
            }
            
            status = "?" if expectancy > 0.2 else "?" if expectancy > 0 else "?"
            print(f"  {regime:15s}  {len(regime_trades):3d}    {win_rate*100:5.1f}%  {pf:6.3f}  {expectancy:+.3f}R    {total_r:+.1f}R  {status}")
        
        return regime_stats
    
    def test_regime_filter(self, data, trades):
        """Test if filtering out bad regimes improves performance."""
        print(f"\n{'='*70}")
        print("  REGIME FILTER TEST")
        print("="*70)
        
        trades_df = pd.DataFrame(trades)
        
        # Find bad regimes
        bad_regimes = []
        for regime in trades_df['regime'].unique():
            regime_trades = trades_df[trades_df['regime'] == regime]
            if len(regime_trades) > 0 and regime_trades['r'].mean() < 0:
                bad_regimes.append(regime)
        
        print(f"\n  Bad regimes to filter: {bad_regimes if bad_regimes else 'None'}")
        
        if not bad_regimes:
            print(f"  All regimes profitable - no filter needed")
            return
        
        # Filter out bad regimes
        good_trades = trades_df[~trades_df['regime'].isin(bad_regimes)]
        
        # Compare
        all_r = trades_df['r'].values
        good_r = good_trades['r'].values
        
        all_expectancy = np.mean(all_r)
        good_expectancy = np.mean(good_r)
        
        all_pf = sum(r for r in all_r if r > 0) / abs(sum(r for r in all_r if r < 0))
        good_pf = sum(r for r in good_r if r > 0) / abs(sum(r for r in good_r if r < 0))
        
        print(f"\n  Performance Comparison:")
        print(f"    All trades:     {len(all_r):3d} trades, {all_expectancy:+.3f}R, PF {all_pf:.3f}")
        print(f"    Filtered:       {len(good_r):3d} trades, {good_expectancy:+.3f}R, PF {good_pf:.3f}")
        print(f"    Improvement:    {good_expectancy - all_expectancy:+.3f}R expectancy")
        
        if good_expectancy > all_expectancy:
            print(f"\n  ? REGIME FILTER IMPROVES PERFORMANCE")
            print(f"  Recommend: Don't trade during {', '.join(bad_regimes)}")
        else:
            print(f"\n  ? Regime filter doesn't help")
    
    def run_full_analysis(self):
        """Run complete regime analysis."""
        print("="*70)
        print("  MARKET REGIME ANALYSIS")
        print("  Testing Strategy Across Different Conditions")
        print("="*70)
        
        data = self.load_data()
        if data is None:
            return None
        
        data = self.classify_regime(data)
        
        # Show regime distribution
        print(f"\nRegime Distribution:")
        regime_counts = data['regime'].value_counts()
        for regime, count in regime_counts.items():
            pct = count / len(data) * 100
            print(f"  {regime}: {count} bars ({pct:.1f}%)")
        
        # Run strategy
        trades = self.run_strategy_with_regime(data)
        
        # Analyze by regime
        regime_stats = self.analyze_regime_performance(trades)
        
        # Test regime filter
        self.test_regime_filter(data, trades)
        
        return regime_stats

if __name__ == "__main__":
    analyzer = RegimeAnalyzer()
    results = analyzer.run_full_analysis()

