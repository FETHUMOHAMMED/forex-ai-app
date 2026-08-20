"""SESSION ANALYSIS - When does the USDJPY edge exist?"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

class SessionAnalyzer:
    """Analyzes strategy performance by trading session."""
    
    def __init__(self):
        self.symbol = "USDJPYm"
        self.timeframe = mt5.TIMEFRAME_H4
        
        # Session definitions (UTC)
        self.sessions = {
            "Asian": (0, 7),        # 00:00-07:00 UTC
            "London": (7, 11),      # 07:00-11:00 UTC
            "Overlap": (11, 13),    # 11:00-13:00 UTC (London/NY overlap)
            "New York": (13, 17),   # 13:00-17:00 UTC
            "Late NY": (17, 21),    # 17:00-21:00 UTC
            "Overnight": (21, 24),  # 21:00-24:00 UTC
        }
        
    def load_data(self):
        """Load historical data."""
        if not mt5.initialize():
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10000)
        mt5.shutdown()
        
        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')
        
        return data
    
    def get_session(self, hour):
        """Determine which session a given hour belongs to."""
        for session_name, (start, end) in self.sessions.items():
            if start <= hour < end:
                return session_name
        return "Unknown"
    
    def run_session_analysis(self):
        """Run strategy across all sessions."""
        print("="*70)
        print("  SESSION ANALYSIS - USDJPY")
        print("  Finding where the edge truly exists")
        print("="*70)
        
        data = self.load_data()
        if data is None:
            return None
        
        # Calculate indicators
        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean()
        
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()
        data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
        data['session'] = data['hour'].apply(self.get_session)
        
        # Run strategy and record session for each trade
        trades = []
        
        for i in range(200, len(data)):
            # BUY only (validated earlier)
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
                            "session": data['session'].iloc[i],
                            "hour": data['hour'].iloc[i],
                            "year": data['timestamp'].iloc[i].year
                        })
                        break
                    elif data['high'].iloc[j] >= tp:
                        trades.append({
                            "r": 2.5,
                            "session": data['session'].iloc[i],
                            "hour": data['hour'].iloc[i],
                            "year": data['timestamp'].iloc[i].year
                        })
                        break
                else:
                    exit_price = data['close'].iloc[exit_idx]
                    r = (exit_price - entry) / (entry - sl)
                    trades.append({
                        "r": r,
                        "session": data['session'].iloc[i],
                        "hour": data['hour'].iloc[i],
                        "year": data['timestamp'].iloc[i].year
                    })
        
        # Analyze by session
        print(f"\n{'='*70}")
        print("  PERFORMANCE BY SESSION")
        print("="*70)
        
        trades_df = pd.DataFrame(trades)
        
        print(f"\n  Session      Trades  WinRate  PF      Expectancy  Total R")
        print(f"  " + "-"*65)
        
        session_stats = {}
        
        for session in ["Asian", "London", "Overlap", "New York", "Late NY", "Overnight"]:
            session_trades = trades_df[trades_df['session'] == session]
            
            if len(session_trades) == 0:
                print(f"  {session:12s}    0     -      -         -          -")
                session_stats[session] = {"trades": 0}
                continue
            
            r_values = session_trades['r'].values
            wins = (r_values > 0).sum()
            win_rate = wins / len(r_values)
            gross_profit = sum(r for r in r_values if r > 0)
            gross_loss = abs(sum(r for r in r_values if r < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            expectancy = np.mean(r_values)
            total_r = sum(r_values)
            
            session_stats[session] = {
                "trades": len(session_trades),
                "win_rate": win_rate,
                "pf": pf,
                "expectancy": expectancy,
                "total_r": total_r
            }
            
            status = "?" if expectancy > 0.2 else "?" if expectancy > 0 else "?"
            print(f"  {session:12s}  {len(session_trades):3d}    {win_rate*100:5.1f}%  {pf:6.3f}  {expectancy:+.3f}R    {total_r:+.1f}R  {status}")
        
        # Statistical tests per session
        print(f"\n{'='*70}")
        print("  STATISTICAL SIGNIFICANCE BY SESSION")
        print("="*70)
        
        for session, stats in session_stats.items():
            if stats["trades"] >= 10:
                session_trades = trades_df[trades_df['session'] == session]
                r_values = session_trades['r'].values
                t_stat, p_value = scipy_stats.ttest_1samp(r_values, 0)
                
                print(f"\n  {session}:")
                print(f"    Trades: {stats['trades']}")
                print(f"    T-statistic: {t_stat:.3f}")
                print(f"    P-value: {p_value:.4f}")
                print(f"    Significant: {'YES ?' if p_value < 0.05 else 'NO'}")
        
        # Hourly breakdown
        print(f"\n{'='*70}")
        print("  HOURLY BREAKDOWN")
        print("="*70)
        
        print(f"\n  Hour (UTC)  Trades  WinRate  PF      Expectancy")
        print(f"  " + "-"*60)
        
        for hour in range(24):
            hour_trades = trades_df[trades_df['hour'] == hour]
            
            if len(hour_trades) < 5:
                continue
            
            r_values = hour_trades['r'].values
            wins = (r_values > 0).sum()
            win_rate = wins / len(r_values)
            gross_profit = sum(r for r in r_values if r > 0)
            gross_loss = abs(sum(r for r in r_values if r < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            expectancy = np.mean(r_values)
            
            status = "?" if expectancy > 0.2 else "?" if expectancy > 0 else "?"
            print(f"  {hour:02d}:00      {len(hour_trades):3d}    {win_rate*100:5.1f}%  {pf:6.3f}  {expectancy:+.3f}R  {status}")
        
        # Best session summary
        print(f"\n{'='*70}")
        print("  KEY FINDINGS")
        print("="*70)
        
        # Find best session
        valid_sessions = {s: stats for s, stats in session_stats.items() if stats["trades"] >= 10}
        if valid_sessions:
            best_session = max(valid_sessions.items(), key=lambda x: x[1]["expectancy"])
            worst_session = min(valid_sessions.items(), key=lambda x: x[1]["expectancy"])
            
            print(f"\n  BEST session: {best_session[0]}")
            print(f"    Expectancy: {best_session[1]['expectancy']:.3f}R")
            print(f"    PF: {best_session[1]['pf']:.3f}")
            
            print(f"\n  WORST session: {worst_session[0]}")
            print(f"    Expectancy: {worst_session[1]['expectancy']:.3f}R")
            print(f"    PF: {worst_session[1]['pf']:.3f}")
            
            print(f"\n  RECOMMENDATION:")
            print(f"    Trade only during: {best_session[0]} session")
            print(f"    Avoid: {worst_session[0]} session")
        
        return session_stats

if __name__ == "__main__":
    analyzer = SessionAnalyzer()
    results = analyzer.run_session_analysis()
