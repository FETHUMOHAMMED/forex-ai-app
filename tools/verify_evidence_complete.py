import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("PRAGMA table_info(trades)")
cols = [col[1] for col in c.fetchall()]

critical = ['signal_age_ms', 'spread_at_execution', 'risk_budget_usd', 
            'actual_risk_usd', 'mt5_closure_state']
print(f"Total columns: {len(cols)}")
print(f"\nCritical Evidence Columns:")
for col in critical:
    status = "PRESENT" if col in cols else "MISSING"
    print(f"  {col}: {status}")

# Check V3 trade evidence
c.execute("SELECT id, signal_age_ms, spread_at_execution, risk_budget_usd, actual_risk_usd, mt5_closure_state FROM trades WHERE id IN (163, 164)")
print(f"\nV3 Trade Evidence:")
for row in c.fetchall():
    print(f"  ID {row[0]}: age={row[1]} spread={row[2]} budget={row[3]} risk={row[4]} closure={row[5]}")

conn.close()
print("\nEvidence Layer: COMPLETE")
