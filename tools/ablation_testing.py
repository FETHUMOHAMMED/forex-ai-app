"""ABLATION TESTING - Which components actually matter?"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

class AblationTester:
    """Tests strategy by removing components one at a time."""
    
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
    
    def calculate_indicators(self, data):
        """Calculate all indicators."""
        df = data.copy()
        
        # EMAs
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        df['atr_ratio'] = df['atr'] / df['atr'].rolling(50).mean()
        
        # Regime
        df['trend_strength'] = abs(df['ema_50'] - df['ema_200']) / df['ema_200'] * 100
        
        df['regime'] = 'UNDEFINED'
        df.loc[(df['ema_20'] > df['ema_50']) & (df['ema_50'] > df['ema_200']) & (df['trend_strength'] > 0.3), 'regime'] = 'TRENDING_BULL'
        df.loc[df['atr_ratio'] < 0.7, 'regime'] = 'LOW_VOLATILITY'
        df.loc[(df['atr_ratio'] > 1.5) & (df['trend_strength'] > 0.3), 'regime'] = 'BREAKOUT'
        df.loc[df['atr_ratio'] > 2.0, 'regime'] = 'HIGH_VOLATILITY'
        df.loc[(df['trend_strength'] <= 0.3) & (df['atr_ratio'] < 1.2), 'regime'] = 'RANGING'
        
        # Session
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['good_session'] = (
            ((df['hour'] >= 0) & (df['hour'] < 7)) |   # Asian
            ((df['hour'] >= 7) & (df['hour'] < 11)) |  # London
            ((df['hour'] >= 17) & (df['hour'] < 21))   # Late NY
        )
        
        # FVG
        df['bullish_fvg'] = False
        df.loc[df['high'].shift(2) < df['low'], 'bullish_fvg'] = True
        
        # Liquidity sweep (simplified)
        df['liquidity_sweep'] = False
        df.loc[df['low'] < df['low'].rolling(20).min().shift(1), 'liquidity_sweep'] = True
        
        # BOS (Break of Structure - simplified)
        df['bos'] = False
        df.loc[df['close'] > df['high'].rolling(10).max().shift(1), 'bos'] = True
        
        # MSS (Market Structure Shift - simplified)
        df['mss'] = False
        df.loc[(df['close'] > df['open']) & (df['close'].shift(1) < df['open'].shift(1)), 'mss'] = True
        
        return df
    
    def run_strategy_variant(self, data, use_fvg=True, use_liquidity=True, 
                            use_bos=True, use_mss=True, use_session=True,
                            use_regime=True, use_atr=True):
        """Run strategy with specific components enabled/disabled."""
        trades = []
        
        for i in range(200, len(data)):
            # Base conditions (always required)
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue  # Must be bullish bias
            
            # Session filter
            if use_session and not data['good_session'].iloc[i]:
                continue
            
            # Regime filter
            if use_regime:
                if data['regime'].iloc[i] in ['RANGING', 'BREAKOUT', 'HIGH_VOLATILITY']:
                    continue
            
            # FVG requirement
            if use_fvg and not data['bullish_fvg'].iloc[i]:
                continue
            
            # Liquidity sweep
            if use_liquidity and not data['liquidity_sweep'].iloc[i]:
                continue
            
            # BOS
            if use_bos and not data['bos'].iloc[i]:
                continue
            
            # MSS
            if use_mss and not data['mss'].iloc[i]:
                continue
            
            # ATR filter (avoid extreme volatility)
            if use_atr:
                if data['atr_ratio'].iloc[i] > 1.5:
                    continue
            
            # If we get here, take the trade
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * 2.0)
            tp = entry + (data['atr'].iloc[i] * 5.0)
            
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({"r": -1})
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({"r": 2.5})
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({"r": r})
        
        return trades
    
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
    
    def run_ablation_test(self):
        """Test strategy by removing each component."""
        print("="*70)
        print("  ABLATION TESTING - Which Components Matter?")
        print("="*70)
        
        data = self.load_data()
        if data is None:
            return None
        
        data = self.calculate_indicators(data)
        
        # Define test variants
        variants = [
            ("FULL STRATEGY", {
                "use_fvg": True, "use_liquidity": True, "use_bos": True,
                "use_mss": True, "use_session": True, "use_regime": True,
                "use_atr": True
            }),
            ("Without FVG", {
                "use_fvg": False, "use_liquidity": True, "use_bos": True,
                "use_mss": True, "use_session": True, "use_regime": True,
                "use_atr": True
            }),
            ("Without Liquidity", {
                "use_fvg": True, "use_liquidity": False, "use_bos": True,
                "use_mss": True, "use_session": True, "use_regime": True,
                "use_atr": True
            }),
            ("Without BOS", {
                "use_fvg": True, "use_liquidity": True, "use_bos": False,
                "use_mss": True, "use_session": True, "use_regime": True,
                "use_atr": True
            }),
            ("Without MSS", {
                "use_fvg": True, "use_liquidity": True, "use_bos": True,
                "use_mss": False, "use_session": True, "use_regime": True,
                "use_atr": True
            }),
            ("Without Session Filter", {
                "use_fvg": True, "use_liquidity": True, "use_bos": True,
                "use_mss": True, "use_session": False, "use_regime": True,
                "use_atr": True
            }),
            ("Without Regime Filter", {
                "use_fvg": True, "use_liquidity": True, "use_bos": True,
                "use_mss": True, "use_session": True, "use_regime": False,
                "use_atr": True
            }),
            ("Without ATR Filter", {
                "use_fvg": True, "use_liquidity": True, "use_bos": True,
                "use_mss": True, "use_session": True, "use_regime": True,
                "use_atr": False
            }),
            ("FVG Only", {
                "use_fvg": True, "use_liquidity": False, "use_bos": False,
                "use_mss": False, "use_session": False, "use_regime": False,
                "use_atr": False
            }),
        ]
        
        print(f"\n{'='*70}")
        print("  RESULTS")
        print("="*70)
        
        print(f"\n  {'Variant':25s} {'Trades':>6s} {'WinRate':>8s} {'PF':>8s} {'Expect':>8s} {'TotalR':>8s}")
        print(f"  " + "-"*70)
        
        results = []
        
        for name, params in variants:
            trades = self.run_strategy_variant(data, **params)
            stats = self.calculate_stats(trades)
            
            results.append({
                "variant": name,
                **stats
            })
            
            print(f"  {name:25s} {stats['trades']:6d} {stats['win_rate']*100:7.1f}% {stats['pf']:8.3f} {stats['expectancy']:+8.3f}R {stats['total_r']:+8.1f}R")
        
        # Analysis
        full_stats = results[0]
        print(f"\n{'='*70}")
        print("  COMPONENT CONTRIBUTION ANALYSIS")
        print("="*70)
        
        print(f"\n  Full strategy: {full_stats['trades']} trades, {full_stats['expectancy']:.3f}R, PF {full_stats['pf']:.3f}")
        
        for i, result in enumerate(results[1:], 1):
            variant_name = variants[i][0]
            removed_component = variant_name.replace("Without ", "")
            
            expectancy_change = full_stats['expectancy'] - result['expectancy']
            pf_change = full_stats['pf'] - result['pf']
            trades_change = full_stats['trades'] - result['trades']
            
            if expectancy_change > 0.1:
                impact = "IMPORTANT"
            elif expectancy_change > 0:
                impact = "MINOR"
            elif expectancy_change < -0.1:
                impact = "HURTS (remove it!)"
            else:
                impact = "NEUTRAL"
            
            print(f"\n  {variant_name}:")
            print(f"    Trades: {result['trades']} (change: {trades_change:+d})")
            print(f"    Expectancy: {result['expectancy']:.3f}R (change: {-expectancy_change:+.3f}R)")
            print(f"    PF: {result['pf']:.3f} (change: {-pf_change:+.3f})")
            print(f"    Impact: {impact}")
        
        return results

if __name__ == "__main__":
    tester = AblationTester()
    results = tester.run_ablation_test()
