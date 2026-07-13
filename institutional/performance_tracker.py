"""
Phase 8: Institutional Performance Tracker
Tracks and compares performance with/without institutional filtering.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-service'))

import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List

@dataclass
class PerformanceSnapshot:
    """Performance metrics at a point in time"""
    timestamp: str
    total_trades: int = 0
    with_inst_data: int = 0
    
    # Overall metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    net_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # By institutional bias
    bullish_trades: int = 0
    bullish_win_rate: float = 0.0
    bearish_trades: int = 0
    bearish_win_rate: float = 0.0
    neutral_trades: int = 0
    
    # By quality grade
    grade_a_trades: int = 0
    grade_a_win_rate: float = 0.0
    grade_b_trades: int = 0
    grade_c_trades: int = 0
    
    # Filter impact
    trades_filtered_by_inst: int = 0
    potential_pnl_saved: float = 0.0  # PnL avoided by filtering


class InstitutionalPerformanceTracker:
    """Tracks institutional module performance over time"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'trades.db')
        self.db_path = db_path
        self.history_file = os.path.join(os.path.dirname(__file__), 'performance_history.json')
    
    def take_snapshot(self) -> PerformanceSnapshot:
        """Capture current performance metrics"""
        conn = sqlite3.connect(self.db_path)
        snap = PerformanceSnapshot(
            timestamp=datetime.now().isoformat()
        )
        
        # Total trades
        c = conn.cursor()
        c.execute('SELECT COUNT(*), SUM(pnl), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) FROM trades WHERE pnl IS NOT NULL')
        row = c.fetchone()
        snap.total_trades = row[0] or 0
        snap.net_pnl = row[1] or 0.0
        wins = row[2] or 0
        snap.win_rate = (wins / snap.total_trades * 100) if snap.total_trades > 0 else 0
        
        # Profit factor
        c.execute('SELECT SUM(pnl) FROM trades WHERE pnl > 0')
        gp = c.fetchone()[0] or 0
        c.execute('SELECT SUM(ABS(pnl)) FROM trades WHERE pnl < 0')
        gl = c.fetchone()[0] or 0
        snap.profit_factor = (gp / gl) if gl > 0 else 0
        
        # Avg win/loss
        c.execute('SELECT AVG(pnl) FROM trades WHERE pnl > 0')
        snap.avg_win = c.fetchone()[0] or 0
        c.execute('SELECT AVG(ABS(pnl)) FROM trades WHERE pnl < 0')
        snap.avg_loss = c.fetchone()[0] or 0
        
        # With institutional data
        c.execute('SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL AND institutional_bias IS NOT NULL')
        snap.with_inst_data = c.fetchone()[0] or 0
        
        # By institutional bias
        c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) FROM trades WHERE pnl IS NOT NULL AND institutional_bias='BULLISH'")
        row = c.fetchone()
        snap.bullish_trades = row[0] or 0
        snap.bullish_win_rate = (row[1]/row[0]*100) if row[0] > 0 else 0
        
        c.execute("SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) FROM trades WHERE pnl IS NOT NULL AND institutional_bias='BEARISH'")
        row = c.fetchone()
        snap.bearish_trades = row[0] or 0
        snap.bearish_win_rate = (row[1]/row[0]*100) if row[0] > 0 else 0
        
        c.execute("SELECT COUNT(*) FROM trades WHERE pnl IS NOT NULL AND institutional_bias='NEUTRAL'")
        snap.neutral_trades = c.fetchone()[0] or 0
        
        conn.close()
        return snap
    
    def save_snapshot(self, snap: PerformanceSnapshot):
        """Save snapshot to history file"""
        history = []
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        
        history.append({
            'timestamp': snap.timestamp,
            'total_trades': snap.total_trades,
            'with_inst_data': snap.with_inst_data,
            'win_rate': snap.win_rate,
            'profit_factor': snap.profit_factor,
            'net_pnl': snap.net_pnl,
            'bullish_win_rate': snap.bullish_win_rate,
            'bearish_win_rate': snap.bearish_win_rate
        })
        
        # Keep last 100 snapshots
        if len(history) > 100:
            history = history[-100:]
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def compare_periods(self, days_before_inst=7):
        """Compare performance before and after institutional module"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff = (datetime.now() - timedelta(days=days_before_inst)).isoformat()
        
        # Before
        c = conn.cursor()
        c.execute('SELECT COUNT(*), SUM(pnl), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) FROM trades WHERE pnl IS NOT NULL AND institutional_bias IS NULL AND timestamp < ?', (cutoff,))
        before = c.fetchone()
        
        # After
        c.execute('SELECT COUNT(*), SUM(pnl), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) FROM trades WHERE pnl IS NOT NULL AND institutional_bias IS NOT NULL AND timestamp >= ?', (cutoff,))
        after = c.fetchone()
        
        conn.close()
        
        before_trades = before[0] or 0
        before_pnl = before[1] or 0
        after_trades = after[0] or 0
        after_pnl = after[1] or 0
        
        before_wr = (before[2]/before_trades*100) if before_trades > 0 else 0
        after_wr = (after[2]/after_trades*100) if after_trades > 0 else 0
        
        return {
            'before': {'trades': before_trades, 'pnl': before_pnl, 'wr': before_wr},
            'after': {'trades': after_trades, 'pnl': after_pnl, 'wr': after_wr}
        }
    
    def print_report(self):
        """Print comprehensive performance report"""
        snap = self.take_snapshot()
        self.save_snapshot(snap)
        
        print("=" * 60)
        print("  INSTITUTIONAL PERFORMANCE REPORT")
        print("=" * 60)
        print(f"  Generated: {snap.timestamp[:19]}")
        print()
        print(f"  Total Trades: {snap.total_trades}")
        print(f"  With Inst Data: {snap.with_inst_data}")
        print(f"  Data Coverage: {snap.with_inst_data/snap.total_trades*100:.0f}%" if snap.total_trades > 0 else "  Data Coverage: 0%")
        print()
        print(f"  Win Rate: {snap.win_rate:.1f}%")
        print(f"  Profit Factor: {snap.profit_factor:.2f}")
        print(f"  Net PnL: ${snap.net_pnl:.2f}")
        print(f"  Avg Win: ${snap.avg_win:.2f}")
        print(f"  Avg Loss: ${snap.avg_loss:.2f}")
        print()
        print("  By Institutional Bias:")
        print(f"    BULLISH: {snap.bullish_trades} trades, WR: {snap.bullish_win_rate:.1f}%")
        print(f"    BEARISH: {snap.bearish_trades} trades, WR: {snap.bearish_win_rate:.1f}%")
        print(f"    NEUTRAL: {snap.neutral_trades} trades")
        print()
        
        # Progress toward validation target
        if snap.with_inst_data < 50:
            remaining = 50 - snap.with_inst_data
            print(f"  ⏳ Need {remaining} more trades with inst data for validation")
        elif snap.with_inst_data < 100:
            print(f"  📊 {snap.with_inst_data}/100 trades - approaching statistical significance")
        else:
            print(f"  ✅ {snap.with_inst_data} trades - sufficient for validation")
        print()


if __name__ == '__main__':
    tracker = InstitutionalPerformanceTracker()
    tracker.print_report()
    
    # Compare periods if enough data
    comparison = tracker.compare_periods()
    if comparison['after']['trades'] > 5:
        print("=" * 60)
        print("  BEFORE vs AFTER INSTITUTIONAL MODULE")
        print("=" * 60)
        print(f"  Before: {comparison['before']['trades']} trades, WR: {comparison['before']['wr']:.1f}%, PnL: ${comparison['before']['pnl']:.2f}")
        print(f"  After:  {comparison['after']['trades']} trades, WR: {comparison['after']['wr']:.1f}%, PnL: ${comparison['after']['pnl']:.2f}")