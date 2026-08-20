"""ENHANCED WALK-FORWARD - 5-8 rolling OOS windows."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

class EnhancedWalkForward:
    """Proper walk-forward with multiple rolling windows."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
    def load_data(self):
        if not mt5.initialize():
            return None
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        data.set_index('timestamp', inplace=True)
        return data
    
    def prepare_features(self, data):
        df = data.copy()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        df['hour'] = df.index.hour
        df['bullish_fvg'] = (df['high'].shift(2) < df['low'])
        return df
    
    def run_strategy(self, data, rr=2.0):
        trades = []
        
        for i in range(200, len(data)):
            if not data['bullish_fvg'].iloc[i]:
                continue
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            
            hour = data['hour'].iloc[i]
            if not ((0 <= hour < 7) or (7 <= hour < 11) or (17 <= hour < 21)):
                continue
            
            entry = data['close'].iloc[i]
            sl = entry - (data['atr'].iloc[i] * 2.0)
            tp = entry + (data['atr'].iloc[i] * 2.0 * rr)
            
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({"r": -1})
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({"r": rr})
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({"r": r})
        
        return trades
    
    def run_walk_forward(self):
        """Run 6 rolling windows."""
        print("="*70)
        print("  ENHANCED WALK-FORWARD (6 Windows)")
        print("="*70)
        
        data = self.load_data()
        data = self.prepare_features(data)
        
        years = sorted(set(data.index.year))
        print(f"\nYears: {years}")
        
        # 6 rolling windows (3-year train, 1-year test)
        windows = []
        for i in range(len(years) - 3):
            train_years = years[i:i+3]
            test_year = years[i+3]
            windows.append((train_years, test_year))
        
        print(f"Windows: {len(windows)}")
        
        all_oos_trades = []
        
        print(f"\n{'Window':>22s} {'Trades':>7s} {'WinRate':>8s} {'PF':>8s} {'Expect':>8s} {'TotalR':>8s}")
        print(f"  " + "-"*65)
        
        for train_years, test_year in windows:
            train_mask = (data.index >= f"{train_years[0]}-01-01") & (data.index <= f"{train_years[-1]}-12-31")
            test_mask = (data.index >= f"{test_year}-01-01") & (data.index <= f"{test_year}-12-31")
            
            train_data = data[train_mask]
            test_data = data[test_mask]
            
            # Test on OOS
            oos_trades = self.run_strategy(test_data, rr=2.0)
            
            if oos_trades:
                r_values = [t["r"] for t in oos_trades]
                wins = sum(1 for r in r_values if r > 0)
                gross_profit = sum(r for r in r_values if r > 0)
                gross_loss = abs(sum(r for r in r_values if r < 0))
                
                win_rate = wins / len(r_values)
                pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                expectancy = np.mean(r_values)
                total_r = sum(r_values)
                
                all_oos_trades.extend(oos_trades)
                
                print(f"  Train {train_years[0]}-{train_years[-1]} ? {test_year}: {len(r_values):3d}   {win_rate*100:5.1f}%  {pf:6.3f}  {expectancy:+6.3f}R  {total_r:+7.1f}R")
        
        # Summary
        if all_oos_trades:
            r_values = [t["r"] for t in all_oos_trades]
            wins = sum(1 for r in r_values if r > 0)
            gross_profit = sum(r for r in r_values if r > 0)
            gross_loss = abs(sum(r for r in r_values if r < 0))
            
            t_stat, p_value = scipy_stats.ttest_1samp(r_values, 0)
            
            print(f"\n{'='*70}")
            print("  COMBINED OOS RESULTS")
            print("="*70)
            print(f"  Trades: {len(r_values)}")
            print(f"  Win rate: {wins/len(r_values)*100:.1f}%")
            print(f"  PF: {gross_profit/gross_loss:.3f}")
            print(f"  Expectancy: {np.mean(r_values):.3f}R")
            print(f"  Total R: {sum(r_values):.1f}")
            print(f"  P-value: {p_value:.4f}")
            print(f"  Significant: {'YES' if p_value < 0.05 else 'NO'}")
        
        return all_oos_trades

if __name__ == "__main__":
    wf = EnhancedWalkForward()
    results = wf.run_walk_forward()
