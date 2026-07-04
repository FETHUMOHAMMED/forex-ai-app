"""
EQUITY CURVE CHART GENERATOR
Generates equity curves from trade history.
Safe for environments without matplotlib.
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Try to import matplotlib – if unavailable, chart generation will be skipped
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib not installed – equity curve charts will be skipped.")

class ChartGenerator:
    def __init__(self, db_path="trades.db"):
        self.db_path = db_path
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_equity_curve(self, days=30, save=True):
        """
        Generate an equity curve chart for the last N days.
        Returns the file path of the saved image, or None if matplotlib is unavailable.
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('''
            SELECT timestamp, pnl 
            FROM trades 
            WHERE exit_price IS NOT NULL AND pnl IS NOT NULL
            ORDER BY timestamp ASC
        ''', conn)
        conn.close()

        if df.empty:
            return None

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['cumulative_pnl'] = df['pnl'].cumsum()

        # Filter to last N days
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff]

        if df.empty:
            return None

        # Create plot
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 5))

        ax.plot(df['timestamp'], df['cumulative_pnl'],
                color='#00ff88', linewidth=2, label='Cumulative P&L')

        # Fill area under curve
        ax.fill_between(df['timestamp'], 0, df['cumulative_pnl'],
                         where=(df['cumulative_pnl'] >= 0),
                         color='#00ff88', alpha=0.3)
        ax.fill_between(df['timestamp'], 0, df['cumulative_pnl'],
                         where=(df['cumulative_pnl'] < 0),
                         color='#ff4444', alpha=0.3)

        # Formatting
        ax.set_title(f'📈 Equity Curve (Last {days} Days)', fontsize=14, fontweight='bold', color='white')
        ax.set_xlabel('Date', fontsize=12, color='#cccccc')
        ax.set_ylabel('Cumulative P&L ($)', fontsize=12, color='#cccccc')
        ax.grid(True, alpha=0.3, color='#666666')
        ax.legend(facecolor='#2d2d2d', edgecolor='none', labelcolor='white')

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45, color='#cccccc')
        plt.yticks(color='#cccccc')

        # Set background colors
        fig.patch.set_facecolor('#1e1e1e')
        ax.set_facecolor('#2d2d2d')

        # Add final value annotation
        final_pnl = df['cumulative_pnl'].iloc[-1]
        color = '#00ff88' if final_pnl >= 0 else '#ff4444'
        ax.annotate(f'${final_pnl:,.2f}',
                    xy=(df['timestamp'].iloc[-1], final_pnl),
                    xytext=(10, 10), textcoords='offset points',
                    color=color, fontweight='bold', fontsize=11)

        plt.tight_layout()

        # Save image
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'equity_curve_{timestamp}.png'
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, facecolor='#1e1e1e')
        plt.close()

        return filepath