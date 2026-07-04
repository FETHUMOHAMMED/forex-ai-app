"""
Daily performance report generator.
Creates an image with key metrics and an equity curve.
"""

import os
import sqlite3
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

class ReportGenerator:
    def __init__(self, db_path="trades.db"):
        self.db_path = db_path
        self.output_dir = os.path.join(os.path.dirname(__file__), 'reports')
        os.makedirs(self.output_dir, exist_ok=True)

    def get_stats(self, days=30):
        """Fetch all necessary statistics from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Overall stats
        cursor.execute('''
            SELECT COUNT(*),
                   SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),
                   SUM(pnl),
                   AVG(confidence),
                   MAX(pnl),
                   MIN(pnl)
            FROM trades
            WHERE exit_price IS NOT NULL AND pnl IS NOT NULL
        ''')
        total, wins, total_pnl, avg_conf, best, worst = cursor.fetchone()
        total = total or 0
        wins = wins or 0
        total_pnl = total_pnl or 0
        avg_conf = avg_conf or 0
        best = best or 0
        worst = worst or 0
        losing = total - wins
        win_rate = (wins / total * 100) if total > 0 else 0

        # Profit factor
        cursor.execute('SELECT SUM(pnl) FROM trades WHERE pnl > 0 AND exit_price IS NOT NULL')
        gross_profit = cursor.fetchone()[0] or 0
        cursor.execute('SELECT SUM(pnl) FROM trades WHERE pnl < 0 AND exit_price IS NOT NULL')
        gross_loss = abs(cursor.fetchone()[0] or 0)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Daily P&L for equity curve (last N days)
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT timestamp, pnl FROM trades
            WHERE exit_price IS NOT NULL AND pnl IS NOT NULL
            AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (cutoff,))
        rows = cursor.fetchall()
        conn.close()

        # Build equity curve
        equity_data = []
        cumulative = 0
        for ts, pnl in rows:
            cumulative += pnl
            equity_data.append((ts[:10], cumulative))

        return {
            'total_trades': total,
            'winning_trades': wins,
            'losing_trades': losing,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'profit_factor': profit_factor,
            'avg_confidence': avg_conf,
            'best_trade': best,
            'worst_trade': worst,
            'equity_curve': equity_data
        }

    def generate_report(self, days=30):
        """Generate the report image and return the file path."""
        stats = self.get_stats(days)

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('#1e1e1e')

        # Metrics text (left side)
        text_lines = [
            f"📊 DAILY PERFORMANCE REPORT",
            f"",
            f"Total Trades:    {stats['total_trades']}",
            f"Win Rate:        {stats['win_rate']:.1f}% ({stats['winning_trades']}W / {stats['losing_trades']}L)",
            f"Total P&L:       ${stats['total_pnl']:,.2f}",
            f"Profit Factor:   {stats['profit_factor']:.2f}",
            f"Avg Confidence:  {stats['avg_confidence']:.1%}",
            f"Best Trade:      ${stats['best_trade']:,.2f}",
            f"Worst Trade:     ${stats['worst_trade']:,.2f}",
        ]
        ax.text(0.05, 0.95, '\n'.join(text_lines), transform=ax.transAxes,
                fontsize=12, verticalalignment='top', fontfamily='monospace',
                color='#cccccc')

        # Equity curve (right side, inset)
        if stats['equity_curve']:
            equity_df = pd.DataFrame(stats['equity_curve'], columns=['date', 'balance'])
            equity_df['date'] = pd.to_datetime(equity_df['date'])
            ax_eq = fig.add_axes([0.55, 0.55, 0.4, 0.4])
            ax_eq.plot(equity_df['date'], equity_df['balance'], color='#00ff88', linewidth=2)
            ax_eq.fill_between(equity_df['date'], 0, equity_df['balance'],
                               where=(equity_df['balance'] >= 0), color='#00ff88', alpha=0.3)
            ax_eq.fill_between(equity_df['date'], 0, equity_df['balance'],
                               where=(equity_df['balance'] < 0), color='#ff4444', alpha=0.3)
            ax_eq.axhline(y=0, color='#666666', linestyle='--', linewidth=1)
            ax_eq.set_facecolor('#2d2d2d')
            ax_eq.tick_params(colors='#cccccc', labelsize=8)
            ax_eq.set_title('Equity Curve', fontsize=10, color='white')

        ax.set_axis_off()

        # Save image
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'daily_report_{timestamp}.png'
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, facecolor='#1e1e1e')
        plt.close()
        return filepath