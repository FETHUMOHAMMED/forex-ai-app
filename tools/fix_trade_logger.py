"""Fix trade_logger.py - P0 data correctness per advisor blueprint"""
import shutil
from pathlib import Path

logger_path = Path("risk/trade_logger.py")

# Read original
with open(logger_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: UTC timestamps in log_trade_entry
old_entry_time = "now_iso = datetime.now().isoformat()"
new_entry_time = "now_iso = datetime.now(timezone.utc).isoformat()"
content = content.replace(old_entry_time, new_entry_time)

# Add timezone import if not present
if 'from datetime import datetime, timezone' not in content:
    content = content.replace(
        'from datetime import datetime, timedelta',
        'from datetime import datetime, timedelta, timezone'
    )

# Fix 2: Add missing fields to INSERT
old_insert = """               (timestamp, pair, signal, confidence, entry, stop_loss, take_profit, volume, ticket, regime, account,
                institutional_bias, institutional_score, dealer_pressure, liquidity_state, continuation_prob)"""

new_insert = """               (timestamp, pair, signal, confidence, entry, stop_loss, take_profit, volume, ticket, regime, account,
                institutional_bias, institutional_score, dealer_pressure, liquidity_state, continuation_prob,
                account_name, trade_mode, strategy_version, environment)"""

content = content.replace(old_insert, new_insert)

# Fix 2b: Add the corresponding VALUES
old_values = """             signal.get('continuation_prob', 0.50))
        )"""

new_values = """             signal.get('continuation_prob', 0.50),
             signal.get('account_name', account),  # Use account param or signal field
             signal.get('trade_mode', 'VALIDATION'),  # Default VALIDATION, not PRODUCTION
             signal.get('strategy_version', 'V3_REGIME'),  # Default V3_REGIME
             signal.get('environment', 'LIVE_MICRO_VALIDATION'))  # Explicit environment
        )"""

content = content.replace(old_values, new_values)

# Fix 3: Correct PnL% calculation
old_pnl_pct = """                if entry_price and entry_price != 0:
                    pnl_percent = (pnl / entry_price) * 100.0   # e.g., 0.15% move
                else:
                    pnl_percent = 0.0"""

new_pnl_pct = """                if entry_price and entry_price != 0:
                    # Calculate return relative to notional value (entry * volume * 100000)
                    self.cursor.execute("SELECT volume FROM trades WHERE ticket=?", (ticket,))
                    vol_row = self.cursor.fetchone()
                    volume = vol_row[0] if vol_row and vol_row[0] else 0.01
                    notional = entry_price * volume * 100000
                    pnl_percent = (pnl / notional) * 100.0 if notional > 0 else 0.0
                else:
                    pnl_percent = 0.0"""

content = content.replace(old_pnl_pct, new_pnl_pct)

# Backup
shutil.copy2(logger_path, logger_path.with_suffix('.py.bak_advisor'))

# Write fixed version
with open(logger_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("=" * 60)
print("  FIXED risk/trade_logger.py")
print("=" * 60)
print("  1. UTC timestamps (entry + exit)")
print("  2. Missing fields: account_name, trade_mode, strategy_version, environment")
print("  3. Default trade_mode = VALIDATION (not PRODUCTION)")
print("  4. Default strategy_version = V3_REGIME")
print("  5. Fixed PnL% formula (notional-based)")
print()
print("  Restart auto_trader to apply fixes")
print("=" * 60)
