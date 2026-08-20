"""USDJPY DEEP EDGE ANALYSIS - Complete breakdown."""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

class USDJPYEdgeAnalyzer:
    """Complete edge analysis for USDJPY."""
    
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
    
    def calculate_features(self, data):
        """Calculate all features."""
        df = data.copy()
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        df['atr_ratio'] = df['atr'] / df['atr'].rolling(50).mean()
        
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.day_name()
        df['bullish_fvg'] = (df['high'].shift(2) < df['low'])
        
        return df
    
    def run_deep_analysis(self):
        """Run complete deep analysis."""
        print("="*70)
        print("  USDJPY DEEP EDGE ANALYSIS")
        print("="*70)
        
        data = self.load_data()
        data = self.calculate_features(data)
        
        trades = []
        
        # Generate all BUY trades
        for i in range(200, len(data)):
            if data['ema_50'].iloc[i] <= data['ema_200'].iloc[i]:
                continue
            if not data['bullish_fvg'].iloc[i]:
                continue
            
            hour = data['hour'].iloc[i]
            if not ((0 <= hour < 7) or (7 <= hour < 11) or (17 <= hour < 21)):
                continue
            
            entry = data['close'].iloc[i]
            atr = data['atr'].iloc[i]
            sl = entry - (atr * 2.0)
            tp = entry + (atr * 4.0)
            
            exit_idx = min(i + 50, len(data) - 1)
            
            for j in range(i+1, exit_idx):
                if data['low'].iloc[j] <= sl:
                    trades.append({
                        "r": -1, "hour": hour, "day": data['day_of_week'].iloc[i],
                        "atr_ratio": data['atr_ratio'].iloc[i],
                        "trend_strength": abs(data['ema_50'].iloc[i] - data['ema_200'].iloc[i]) / data['ema_200'].iloc[i] * 100,
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month,
                        "result": "SL"
                    })
                    break
                elif data['high'].iloc[j] >= tp:
                    trades.append({
                        "r": 2.0, "hour": hour, "day": data['day_of_week'].iloc[i],
                        "atr_ratio": data['atr_ratio'].iloc[i],
                        "trend_strength": abs(data['ema_50'].iloc[i] - data['ema_200'].iloc[i]) / data['ema_200'].iloc[i] * 100,
                        "year": data['timestamp'].iloc[i].year,
                        "month": data['timestamp'].iloc[i].month,
                        "result": "TP"
                    })
                    break
            else:
                exit_price = data['close'].iloc[exit_idx]
                r = (exit_price - entry) / (entry - sl)
                trades.append({
                    "r": r, "hour": hour, "day": data['day_of_week'].iloc[i],
                    "atr_ratio": data['atr_ratio'].iloc[i],
                    "trend_strength": abs(data['ema_50'].iloc[i] - data['ema_200'].iloc[i]) / data['ema_200'].iloc[i] * 100,
                    "year": data['timestamp'].iloc[i].year,
                    "month": data['timestamp'].iloc[i].month,
                    "result": "TIMEOUT"
                })
        
        trades_df = pd.DataFrame(trades)
        
        # 1. Basic stats
        print(f"\n1. BASIC STATISTICS")
        r_values = trades_df['r'].values
        print(f"   Trades: {len(r_values)}")
        print(f"   Win rate: {(r_values > 0).mean()*100:.1f}%")
        print(f"   PF: {sum(r for r in r_values if r > 0) / abs(sum(r for r in r_values if r < 0)):.3f}")
        print(f"   Expectancy: {np.mean(r_values):.3f}R")
        
        # 2. Hour analysis
        print(f"\n2. HOURLY ANALYSIS")
        for hour in sorted(trades_df['hour'].unique()):
            h_trades = trades_df[trades_df['hour'] == hour]
            print(f"   {hour:02d}:00 - {len(h_trades):3d} trades, {h_trades['r'].mean():+.3f}R")
        
        # 3. Day of week
        print(f"\n3. DAY OF WEEK ANALYSIS")
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            d_trades = trades_df[trades_df['day'] == day]
            if len(d_trades) > 0:
                print(f"   {day}: {len(d_trades):3d} trades, {d_trades['r'].mean():+.3f}R")
        
        # 4. ATR ratio
        print(f"\n4. VOLATILITY (ATR Ratio) ANALYSIS")
        trades_df['vol_bucket'] = pd.cut(trades_df['atr_ratio'], bins=[0, 0.7, 1.0, 1.3, 1.6, 3.0])
        for bucket in trades_df['vol_bucket'].unique():
            b_trades = trades_df[trades_df['vol_bucket'] == bucket]
            print(f"   ATR Ratio {bucket}: {len(b_trades):3d} trades, {b_trades['r'].mean():+.3f}R")
        
        # 5. Trend strength
        print(f"\n5. TREND STRENGTH ANALYSIS")
        trades_df['trend_bucket'] = pd.cut(trades_df['trend_strength'], bins=[0, 0.1, 0.3, 0.5, 1.0, 5.0])
        for bucket in trades_df['trend_bucket'].unique():
            b_trades = trades_df[trades_df['trend_bucket'] == bucket]
            print(f"   Trend {bucket}%: {len(b_trades):3d} trades, {b_trades['r'].mean():+.3f}R")
        
        # 6. Monthly
        print(f"\n6. MONTHLY PERFORMANCE")
        trades_df['month_key'] = trades_df['year'].astype(str) + '-' + trades_df['month'].astype(str).str.zfill(2)
        monthly = trades_df.groupby('month_key')['r'].agg(['sum', 'count'])
        profitable_months = (monthly['sum'] > 0).sum()
        print(f"   Profitable months: {profitable_months}/{len(monthly)}")
        print(f"   Best month: {monthly['sum'].max():+.1f}R")
        print(f"   Worst month: {monthly['sum'].min():+.1f}R")
        
        # 7. Yearly
        print(f"\n7. YEARLY PERFORMANCE")
        yearly = trades_df.groupby('year')['r'].agg(['sum', 'count'])
        for year, row in yearly.iterrows():
            print(f"   {year}: {row['sum']:+.1f}R in {row['count']} trades")
        
        # 8. Consecutive wins/losses
        print(f"\n8. CONSECUTIVE STREAKS")
        max_win = 0
        max_loss = 0
        cur_win = 0
        cur_loss = 0
        for r in r_values:
            if r > 0:
                cur_win += 1
                cur_loss = 0
                max_win = max(max_win, cur_win)
            else:
                cur_loss += 1
                cur_win = 0
                max_loss = max(max_loss, cur_loss)
        print(f"   Max consecutive wins: {max_win}")
        print(f"   Max consecutive losses: {max_loss}")
        
        return trades_df

if __name__ == "__main__":
    analyzer = USDJPYEdgeAnalyzer()
    results = analyzer.run_deep_analysis()
