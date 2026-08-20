"""Fix trade_logger to capture actual MT5 execution data"""
import shutil
from pathlib import Path

logger_path = Path("risk/trade_logger.py")

with open(logger_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The current log_trade_entry stores signal['entry'] - which is the PLANNED price
# We need to also accept and store the ACTUAL execution price from MT5

# Fix 1: Update log_trade_entry signature to accept actual execution data
old_sig = """    def log_trade_entry(self, signal, volume=None, ticket=None, regime=None, account=None):
        now_iso = datetime.now(timezone.utc).isoformat()
        self.cursor.execute(
            \"\"\"INSERT INTO trades
               (timestamp, pair, signal, confidence, entry, stop_loss, take_profit, volume, ticket, regime, account,
                institutional_bias, institutional_score, dealer_pressure, liquidity_state, continuation_prob,
                account_name, trade_mode, strategy_version, environment)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
            (now_iso, signal['pair'], signal['signal'], signal['confidence'],
             signal['entry'], signal['stop_loss'], signal['take_profit'],
             volume, ticket, regime, account,
             signal.get('institutional_bias', 'NEUTRAL'),
             signal.get('institutional_score', 0),
             signal.get('dealer_pressure', 'NEUTRAL'),
             signal.get('liquidity_state', 'NO_EVENT'),
             signal.get('continuation_prob', 0.50),
             signal.get('account_name', account),
             signal.get('trade_mode', 'VALIDATION'),
             signal.get('strategy_version', 'V3_REGIME'),
             signal.get('environment', 'LIVE_MICRO_VALIDATION'))
        )
        self.conn.commit()
        return self.cursor.lastrowid"""

new_sig = """    def log_trade_entry(self, signal, volume=None, ticket=None, regime=None, account=None,
                         actual_entry=None, actual_sl=None, actual_tp=None, mt5_position_id=None):
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Use actual execution prices if provided, otherwise fall back to signal prices
        entry_price = actual_entry if actual_entry is not None else signal['entry']
        sl_price = actual_sl if actual_sl is not None else signal['stop_loss']
        tp_price = actual_tp if actual_tp is not None else signal['take_profit']
        position_id = mt5_position_id if mt5_position_id is not None else ticket
        
        self.cursor.execute(
            \"\"\"INSERT INTO trades
               (timestamp, pair, signal, confidence, entry, stop_loss, take_profit, volume, ticket, regime, account,
                institutional_bias, institutional_score, dealer_pressure, liquidity_state, continuation_prob,
                account_name, trade_mode, strategy_version, environment,
                planned_entry, planned_sl, planned_tp, mt5_position_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
            (now_iso, signal['pair'], signal['signal'], signal['confidence'],
             entry_price, sl_price, tp_price,
             volume, ticket, regime, account,
             signal.get('institutional_bias', 'NEUTRAL'),
             signal.get('institutional_score', 0),
             signal.get('dealer_pressure', 'NEUTRAL'),
             signal.get('liquidity_state', 'NO_EVENT'),
             signal.get('continuation_prob', 0.50),
             signal.get('account_name', account),
             signal.get('trade_mode', 'VALIDATION'),
             signal.get('strategy_version', 'V3_REGIME'),
             signal.get('environment', 'LIVE_MICRO_VALIDATION'),
             signal['entry'], signal['stop_loss'], signal['take_profit'],
             position_id)
        )
        self.conn.commit()
        return self.cursor.lastrowid"""

content = content.replace(old_sig, new_sig)

# Fix 2: Add planned columns to migration
old_migration = """            ('continuation_prob', 'REAL')
        ]:"""

new_migration = """            ('continuation_prob', 'REAL'),
            ('planned_entry', 'REAL'),
            ('planned_sl', 'REAL'),
            ('planned_tp', 'REAL'),
            ('mt5_position_id', 'INTEGER')
        ]:"""

content = content.replace(old_migration, new_migration)

# Backup
shutil.copy2(logger_path, logger_path.with_suffix('.py.bak_v2'))

with open(logger_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("=" * 60)
print("  FIXED trade_logger.py - Execution Capture")
print("=" * 60)
print("  1. Accepts actual_entry, actual_sl, actual_tp, mt5_position_id")
print("  2. Stores planned (signal) prices separately")
print("  3. Stores actual execution prices as the primary entry/sl/tp")
print("  4. Stores mt5_position_id for exact reconciliation")
print()
print("  Next: Update auto_trader to pass actual MT5 fill data")
print("=" * 60)
