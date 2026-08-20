"""Tag historical invalid records as LEGACY_INVALID - preserves provenance"""
import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 60)
print("  HISTORICAL DATA CLEANUP")
print("=" * 60)

# 1. Tag contaminated records (account mismatch)
c.execute("""
    UPDATE trades SET 
        result = CASE WHEN result IN ('WIN','LOSS','BREAKEVEN') THEN 'LEGACY_INVALID_' || result ELSE 'LEGACY_INVALID' END,
        reason = 'Account contamination: account/account_name mismatch'
    WHERE account = 'Live_Micro' AND account_name = 'Demo2'
    AND result NOT LIKE 'LEGACY%'
""")
contam = c.rowcount
print(f"Tagged {contam} contaminated records as LEGACY_INVALID")

# 2. Tag timestamp errors
c.execute("""
    UPDATE trades SET 
        result = CASE WHEN result IN ('WIN','LOSS','BREAKEVEN') THEN 'LEGACY_INVALID_' || result ELSE 'LEGACY_INVALID' END,
        reason = 'Timestamp corruption: exit before entry'
    WHERE exit_time IS NOT NULL AND timestamp IS NOT NULL 
    AND exit_time < timestamp
    AND result NOT LIKE 'LEGACY%'
""")
ts_errors = c.rowcount
print(f"Tagged {ts_errors} timestamp-error records as LEGACY_INVALID")

# 3. Tag phantom trade (ID 146)
c.execute("""
    UPDATE trades SET 
        result = 'LEGACY_INVALID_PHANTOM',
        reason = 'Phantom trade: not an MT5 position ticket'
    WHERE id = 146 AND result NOT LIKE 'LEGACY%'
""")
phantoms = c.rowcount
print(f"Tagged {phantoms} phantom records as LEGACY_INVALID")

# 4. Tag sizing violations on Live_Micro
c.execute("""
    UPDATE trades SET 
        result = CASE WHEN result IN ('WIN','LOSS','BREAKEVEN') THEN 'LEGACY_INVALID_' || result ELSE 'LEGACY_INVALID' END,
        reason = 'Sizing violation: volume >= 0.1 on Live_Micro'
    WHERE account = 'Live_Micro' AND volume >= 0.1
    AND result NOT LIKE 'LEGACY%'
""")
sizing = c.rowcount
print(f"Tagged {sizing} sizing-violation records as LEGACY_INVALID")

conn.commit()

# Show clean counts
c.execute("SELECT COUNT(*) FROM trades WHERE result NOT LIKE 'LEGACY%' AND strategy_version = 'V3_REGIME' AND account = 'Live_Micro'")
clean_v3 = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM trades WHERE result LIKE 'LEGACY%'")
legacy = c.fetchone()[0]

print(f"\nClean V3 Live_Micro records: {clean_v3}")
print(f"Legacy-invalid records (preserved): {legacy}")
print(f"Total records: {clean_v3 + legacy}")

conn.close()
print("\nDone. Historical data tagged, not deleted. Clean V3 counting can now proceed.")
