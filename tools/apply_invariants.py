"""Apply domain invariants to trade_logger - replaces post-hoc fixes"""
import sys
from pathlib import Path
sys.path.insert(0, '.')

logger_path = Path("packages/persistence/trade_logger.py")
if not logger_path.exists():
    logger_path = Path("risk/trade_logger.py")  # fallback to old location

if not logger_path.exists():
    print("trade_logger.py not found")
    exit()

with open(logger_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add invariant import
if 'from packages.domain.invariants import' not in content:
    import_line = '\nfrom packages.domain.invariants import TradeInvariants, DataIntegrityError, enforce_invariants\n'
    content = content.replace('import sqlite3', 'import sqlite3' + import_line)

# Add invariant check in log_trade_entry BEFORE insert
old_entry = '        self.cursor.execute('
new_entry = '''        # Enforce domain invariants before insertion
        trade_data = {
            'mt5_position_id': mt5_position_id,
            'entry': entry_price,
            'account': account,
            'account_name': signal.get('account_name', account),
            'strategy_version': signal.get('strategy_version', 'V3_REGIME'),
            'timestamp': now_iso,
            'volume': volume,
            'environment': signal.get('environment', 'LIVE_MICRO_VALIDATION'),
            'trade_mode': signal.get('trade_mode', 'VALIDATION'),
        }
        violations = TradeInvariants.validate_on_open(trade_data)
        if violations:
            print(f"[INVARIANT] Trade rejected - {len(violations)} violations:")
            for v in violations:
                print(f"  [{v.severity}] {v.rule}: {v.detail}")
            enforce_invariants(violations)
        
        self.cursor.execute('''

content = content.replace(old_entry, new_entry, 1)  # Only first occurrence

# Write back
import shutil
shutil.copy2(logger_path, logger_path.with_suffix('.py.bak_inv'))

with open(logger_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Applied invariants to {logger_path}")
print("Future trades will be rejected if they violate:")
print("  - MUST_HAVE_MT5_POSITION")
print("  - ENTRY_NOT_STALE_SIGNAL")
print("  - ACCOUNT_NAME_CONSISTENT")
print("  - STRATEGY_VERSION_REQUIRED")
print("  - TIMESTAMP_HAS_TIMEZONE")
print("  - VOLUME_REASONABLE_FOR_ACCOUNT")
