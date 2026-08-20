"""P0: Fix execution contract validation - SL/TP must be valid for ACTUAL fill"""
import sqlite3

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# Add execution contract columns
for col, col_type in [
    ('entry_deviation_pips', 'REAL'),
    ('execution_contract_valid', 'INTEGER DEFAULT 0'),
    ('execution_issue', 'TEXT'),
]:
    try:
        c.execute(f"ALTER TABLE trades ADD COLUMN {col} {col_type}")
        print(f"Added column: {col}")
    except:
        pass

# Analyze ID 163
c.execute("""
    SELECT id, signal, entry, stop_loss, take_profit, planned_entry 
    FROM trades WHERE id = 163
""")
r = c.fetchone()
tid, direction, entry, sl, tp, planned = r

deviation = abs(entry - planned) * 10000

# Check execution contract
if direction == 'SELL':
    sl_valid = sl > entry
    tp_valid = tp < entry
else:
    sl_valid = sl < entry
    tp_valid = tp > entry

issues = []
if not sl_valid: issues.append(f"SL_INVALID: SL({sl}) on wrong side of entry({entry}) for {direction}")
if not tp_valid: issues.append(f"TP_INVALID: TP({tp}) on wrong side of entry({entry}) for {direction}")
if deviation > 5: issues.append(f"EXTREME_DEVIATION: {deviation:.1f} pips")
if planned == 1.15123: issues.append("STALE_SIGNAL: planned entry matches known stale cache value")

contract_valid = len(issues) == 0

# Update the record
c.execute("""
    UPDATE trades SET 
        entry_deviation_pips = ?,
        execution_contract_valid = ?,
        execution_issue = ?,
        result = CASE WHEN ? = 0 AND result NOT LIKE 'LEGACY%' THEN 'EXECUTION_EXCEPTION' ELSE result END
    WHERE id = ?
""", (deviation, 1 if contract_valid else 0, '; '.join(issues) if issues else None,
      contract_valid, tid))

conn.commit()

print(f"\nID {tid} Execution Contract Analysis:")
print(f"  Direction: {direction}")
print(f"  Planned Entry: {planned}")
print(f"  Actual Entry:  {entry}")
print(f"  Deviation: {deviation:.1f} pips")
print(f"  SL Valid: {sl_valid} (SL={sl} vs Entry={entry})")
print(f"  TP Valid: {tp_valid} (TP={tp} vs Entry={entry})")
print(f"  Contract Valid: {contract_valid}")
if issues:
    print(f"  Issues:")
    for i in issues:
        print(f"    - {i}")
    print(f"\n  VERDICT: Reclassified as EXECUTION_EXCEPTION")
    print(f"  This trade NO LONGER counts toward execution integrity")
    print(f"  Reason: The SL was on the wrong side of actual fill")

# Show updated V3 status
c.execute("""
    SELECT COUNT(*) FROM trades 
    WHERE strategy_version='V3_REGIME' AND account='Live_Micro'
    AND result NOT LIKE 'LEGACY%' AND result != 'EXECUTION_EXCEPTION'
    AND execution_contract_valid = 1
    AND result IN ('WIN','LOSS','BREAKEVEN')
""")
clean = c.fetchone()[0]
print(f"\n  Clean V3 trades after P0 fix: {clean}")
print(f"  Execution Integrity: {clean}/10 (was incorrectly 1/10)")

conn.close()
