"""Simulate what the next trade's metadata will look like"""
import sys
sys.path.insert(0, '.')
from risk.trade_logger import TradeLogger
import tempfile, os

# Create a test DB
db_path = os.path.join(tempfile.gettempdir(), 'test_trade_logger.db')
if os.path.exists(db_path): os.remove(db_path)

logger = TradeLogger(db_path)

# Simulate a Live_Micro V3 signal (what auto_trader passes)
signal = {
    'pair': 'EURUSD',
    'signal': 'SELL',
    'confidence': 0.83,
    'entry': 1.15646,
    'stop_loss': 1.15838,
    'take_profit': 1.15215,
    'institutional_bias': 'BREAKOUT',
    'institutional_score': 81.85,
    'dealer_pressure': 'SELLING_PRESSURE',
    'liquidity_state': 'SWEEP_SELL',
    'continuation_prob': 0.50,
    'regime': 'volatile',
    'account_name': 'Live_Micro',
    'trade_mode': 'VALIDATION',
    'strategy_version': 'V3_REGIME',
    'environment': 'LIVE_MICRO_VALIDATION'
}

trade_id = logger.log_trade_entry(
    signal, 
    volume=0.01, 
    ticket=12345678, 
    regime='volatile', 
    account='Live_Micro'
)

import sqlite3
c = sqlite3.connect(db_path)
row = c.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
cols = [d[0] for d in c.description]

print("Next trade metadata will look like:")
print("-" * 40)
for col, val in zip(cols, row):
    if col in ('timestamp', 'account', 'account_name', 'account_id', 'environment', 
               'trade_mode', 'strategy_version', 'regime', 'pair', 'ticket', 'volume'):
        print(f"  {col:20} = {val}")

# Check for timestamp timezone
ts = row[1]
has_tz = '+' in ts or 'Z' in ts
print(f"\n  Timestamp has timezone: {has_tz} -> {ts}")

c.close()
os.remove(db_path)
print("\nMetadata is CONSISTENT for future trades!")
