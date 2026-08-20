"""Fix conflicting metadata on V3 trades per advisor blueprint"""
import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("=" * 60)
print("  FIXING V3 TRADE METADATA")
print("=" * 60)

# ID 146: BREAKEVEN on Live_Micro - already mostly clean
c.execute("""
    UPDATE trades SET 
        account_name = 'Live_Micro',
        account_id = REDACTED_LIVE_ACCOUNT,
        environment = 'LIVE_MICRO',
        trade_mode = 'VALIDATION'
    WHERE id = 146
""")
print("ID 146: account_name -> Live_Micro, environment -> LIVE_MICRO")

# ID 162: LOSS on Demo2 - tag correctly as demo
c.execute("""
    UPDATE trades SET 
        account_name = 'Demo2',
        account_id = REDACTED_DEMO_ACCOUNT,
        environment = 'DEMO',
        trade_mode = 'VALIDATION',
        regime = 'volatile'
    WHERE id = 162
""")
print("ID 162: Tagged as Demo2 demo trade, regime -> volatile")

# ID 163: OPEN on Live_Micro - correct metadata
c.execute("""
    UPDATE trades SET 
        account_name = 'Live_Micro',
        account_id = REDACTED_LIVE_ACCOUNT,
        environment = 'LIVE_MICRO_VALIDATION',
        trade_mode = 'VALIDATION',
        regime = 'volatile'
    WHERE id = 163
""")
print("ID 163: account_name -> Live_Micro, regime -> volatile")

conn.commit()

# Verify
print("\n--- VERIFICATION ---")
c.execute("""
    SELECT id, account, account_name, account_id, environment, 
           trade_mode, strategy_version, regime, result
    FROM trades WHERE strategy_version = 'V3_REGIME'
""")
for row in c.fetchall():
    print(f"  ID {row[0]}: acct={row[1]} acct_name={row[2]} acct_id={row[3]} env={row[4]} mode={row[5]} regime={row[7]} result={row[8]}")

conn.close()
print("\nMetadata cleaned. Next: fix the validation counter to only count Live_Micro CLOSED trades.")
