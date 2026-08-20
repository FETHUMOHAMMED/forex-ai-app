import sqlite3
c = sqlite3.connect('ai-service/trades.db')

print("=" * 80)
print("  FULL SCHEMA & RAW V3 DATA")
print("=" * 80)

print("\n--- COLUMNS ---")
cols = c.execute("PRAGMA table_info(trades)").fetchall()
for col in cols:
    print(f"  {col[0]:3} {col[1]:25} {col[2]:15} nullable={col[3]} default={col[4]}")

print("\n--- V3 REGIME RAW RECORDS ---")
rows = c.execute("SELECT * FROM trades WHERE strategy_version = 'V3_REGIME' ORDER BY id").fetchall()
col_names = [col[1] for col in cols]

for row in rows:
    print(f"\n  ID: {row[0]}")
    for i, (name, val) in enumerate(zip(col_names, row)):
        if val is not None:
            print(f"    {name:25} = {str(val)[:80]}")

print("\n--- SIGNAL CACHE CHECK ---")
import json
try:
    with open('ai-service/signals_cache.json', 'r') as f:
        cache = json.load(f)
    eurusd = cache.get('EURUSD', {})
    print(f"  Cached EURUSD signal:")
    for k, v in eurusd.items():
        print(f"    {k}: {v}")
except:
    print("  Could not read signals cache")

print("\n--- TIMESTAMP ANALYSIS ---")
for row in rows:
    id_, ts, exit_ts = row[0], row[1], row[9]  # timestamp, exit_time
    result = row[11]  # result
    print(f"  ID {id_}: entry={ts[:19] if ts else 'NULL'} | exit={exit_ts[:19] if exit_ts else 'NULL'} | result={result}")
    if ts and exit_ts:
        from datetime import datetime
        try:
            t1 = datetime.fromisoformat(ts)
            t2 = datetime.fromisoformat(exit_ts)
            diff = (t2 - t1).total_seconds()
            if diff < 0:
                print(f"    WARNING: Exit before entry by {-diff:.0f} seconds!")
        except:
            pass

c.close()
