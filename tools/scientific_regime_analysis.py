"""SCIENTIFIC REGIME ANALYSIS - Measurable, not vague."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

class ScientificRegimeAnalyzer:
    """Classifies regimes with precise, measurable criteria."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
    def load_data(self):
        """Load historical data."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        return data
    
    def classify_regime_scientifically(self, data):
        """Classify regime with precise mathematical definitions."""
        df = data.copy()
        
        # Calculate indicators
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        # ATR for volatility
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        df['atr_ma_50'] = df['atr'].rolling(50).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma_50']
        
        # ADX for trend strength
        df['trend_strength'] = abs(df['ema_50'] - df['ema_200']) / df['ema_200'] * 100
        
        # Bollinger Band width for volatility
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_width'] = (df['bb_std'] * 2) / df['close'] * 100
        
        # Classify regimes with PRECISE thresholds
        df['regime'] = 'UNDEFINED'
        
        # TRENDING_BULL: EMA20 > EMA50 > EMA200 AND trend strength > threshold
        df.loc[
            (df['ema_20'] > df['ema_50']) & 
            (df['ema_50'] > df['ema_200']) & 
            (df['trend_strength'] > 0.3),
            'regime'
        ] = 'TRENDING_BULL'
        
        # TRENDING_BEAR: EMA20 < EMA50 < EMA200 AND trend strength > threshold
        df.loc[
            (df['ema_20'] < df['ema_50']) & 
            (df['ema_50'] < df['ema_200']) & 
            (df['trend_strength'] > 0.3),
            'regime'
        ] = 'TRENDING_BEAR'
        
        # RANGING: EMAs close together AND low trend strength
        df.loc[
            (df['trend_strength'] <= 0.3) & 
            (df['atr_ratio'] < 1.2),
            'regime'
        ] = 'RANGING'
        
        # BREAKOUT: High volatility AND price breaking recent range
        df.loc[
            (df['atr_ratio'] > 1.5) & 
            (df['trend_strength'] > 0.3),
            'regime'
        ] = 'BREAKOUT'
        
        # HIGH_VOLATILITY: ATR ratio very high
        df.loc[
            df['atr_ratio'] > 2.0,
            'regime'
        ] = 'HIGH_VOLATILITY'
        
        # LOW_VOLATILITY: ATR ratio very low
        df.loc[
            df['atr_ratio'] < 0.7,
            'regime'
        ] = 'LOW_VOLATILITY'
        
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        return df
    
    def run_strategy_with_regime(self, data):
        """Run strategy and record regime for each trade."""
        trades = []
        
        for i in range(200, len(data)):
            # BUY only (validated)
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            # Only trade during favorable sessions
            hour = data['hour'].iloc[i]
            in_good_session = (
                (0 <= hour < 7) or    # Asian
                (7 <= hour < 11) or   # London
                (17 <= hour < 21)     # Late NY
            )
            
            if not in_good_session:
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
        print("  STRATEGY PERFORMANCE BY SCIENTIFIC REGIME")
        print("="*70)
        
        regimes = ['TRENDING_BULL', 'TRENDING_BEAR', 'RANGING', 'BREAKOUT', 'HIGH_VOLATILITY', 'LOW_VOLATILITY', 'UNDEFINED']
        
        print(f"\n  Regime            Trades  WinRate  PF      Expectancy  Total R")
        print(f"  " + "-"*70)
        
        regime_stats = {}
        
        for regime in regimes:
            regime_trades = trades_df[trades_df['regime'] == regime]
            
            if len(regime_trades) == 0:
                print(f"  {regime:18s}    0     -      -         -          -")
                continue
            
            r_values = regime_trades['r'].values
            wins = (r_values > 0).sum()
            win_rate = wins / len(r_values)
            gross_profit = sum(r for r in r_values if r > 0)
            gross_loss = abs(sum(r for r in r_values if r < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            expectancy = np.mean(r_values)
            total_r = sum(r_values)
            
            # Statistical test
            if len(r_values) >= 10:
                t_stat, p_value = scipy_stats.ttest_1samp(r_values, 0)
            else:
                t_stat, p_value = 0, 1.0
            
            regime_stats[regime] = {
                "trades": len(regime_trades),
                "win_rate": win_rate,
                "pf": pf,
                "expectancy": expectancy,
                "total_r": total_r,
                "p_value": p_value
            }
            
            status = "?" if expectancy > 0.2 else "?" if expectancy > 0 else "?"
            sig = "?" if p_value < 0.05 else ""
            print(f"  {regime:18s}  {len(regime_trades):3d}    {win_rate*100:5.1f}%  {pf:6.3f}  {expectancy:+.3f}R    {total_r:+.1f}R  {status} {sig}")
        
        return regime_stats
    
    def create_regime_filter(self, regime_stats):
        """Create regime-based trading filter."""
        print(f"\n{'='*70}")
        print("  REGIME FILTER RECOMMENDATION")
        print("="*70)
        
        # Classify regimes
        trade_regimes = []
        avoid_regimes = []
        
        for regime, stats in regime_stats.items():
            if stats["trades"] >= 10:
                if stats["expectancy"] > 0.15 and stats["pf"] > 1.2:
                    trade_regimes.append(regime)
                elif stats["expectancy"] < 0:
                    avoid_regimes.append(regime)
        
        print(f"\n  TRADE in these regimes:")
        for regime in trade_regimes:
            print(f"    ? {regime}")
        
        print(f"\n  AVOID these regimes:")
        for regime in avoid_regimes:
            print(f"    ? {regime}")
        
        print(f"\n  RECOMMENDED FILTER:")
        print(f"  IF regime in {trade_regimes} ? TRADE")
        print(f"  IF regime in {avoid_regimes} ? NO TRADE")
        
        return trade_regimes, avoid_regimes
    
    def run_full_analysis(self):
        """Run complete scientific regime analysis."""
        print("="*70)
        print("  SCIENTIFIC REGIME ANALYSIS")
        print("  Precise, Measurable, Reproducible")
        print("="*70)
        
        data = self.load_data()
        if data is None:
            return None
        
        data = self.classify_regime_scientifically(data)
        
        # Show regime distribution
        print(f"\n  Regime Distribution:")
        regime_counts = data['regime'].value_counts()
        for regime, count in regime_counts.items():
            pct = count / len(data) * 100
            print(f"    {regime}: {count} bars ({pct:.1f}%)")
        
        # Run strategy
        trades = self.run_strategy_with_regime(data)
        
        # Analyze by regime
        regime_stats = self.analyze_regime_performance(trades)
        
        # Create filter
        trade_regimes, avoid_regimes = self.create_regime_filter(regime_stats)
        
        return regime_stats

if __name__ == "__main__":
    analyzer = ScientificRegimeAnalyzer()
    results = analyzer.run_full_analysis()
