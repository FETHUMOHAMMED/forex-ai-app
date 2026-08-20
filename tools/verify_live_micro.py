import sqlite3
c = sqlite3.connect('ai-service/trades.db')

print("=" * 60)
print("  V3 Live_Micro - Source Data Verification")
print("=" * 60)

rows = c.execute("""
    SELECT id, pair, ticket, account, account_name, account_id, 
           environment, strategy_version, result, pnl, exit_time
    FROM trades 
    WHERE strategy_version = 'V3_REGIME' AND account = 'Live_Micro'
    ORDER BY id
""").fetchall()

print(f"\nLive_Micro V3 trades: {len(rows)}")
for r in rows:
    print(f"\n  ID {r[0]}: {r[1]} | Ticket: {r[2]}")
    print(f"    account={r[3]} | account_name={r[4]} | account_id={r[5]}")
    print(f"    environment={r[6]} | strategy={r[7]}")
    print(f"    result={r[8]} | pnl={r[9]} | exit={str(r[10])[:19] if r[10] else 'OPEN'}")

# Check for metadata inconsistencies
print("\n--- INCONSISTENCY CHECK ---")
for r in rows:
    issues = []
    if r[3] == 'Live_Micro' and r[4] != 'Live_Micro':
        issues.append(f"account_name mismatch: {r[4]}")
    if r[5] != REDACTED_LIVE_ACCOUNT:
        issues.append(f"account_id mismatch: {r[5]}")
    if r[8] and r[9] is None:
        issues.append("closed but no PnL")
    if r[10] and r[9] is None:
        issues.append("has exit_time but no PnL")
    if issues:
        print(f"  ID {r[0]}: {', '.join(issues)}")

if not any(r[3] == 'Live_Micro' and r[4] != 'Live_Micro' for r in rows):
    print("  account/account_name: CONSISTENT")

c.close()
