"""Create proper execution ledger with all advisor-required fields"""
import sqlite3

conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS execution_ledger (
        ledger_id TEXT PRIMARY KEY,
        signal_id TEXT,
        order_intent_id TEXT,
        execution_attempt_id TEXT,
        position_ticket INTEGER,
        opening_deal_ticket INTEGER,
        closing_deal_ticket INTEGER,
        account_id INTEGER,
        planned_entry REAL,
        actual_entry REAL,
        planned_sl REAL,
        actual_sl REAL,
        planned_tp REAL,
        actual_tp REAL,
        planned_volume REAL,
        actual_volume REAL,
        slippage_pips REAL,
        risk_budget_usd REAL,
        actual_risk_usd REAL,
        execution_status TEXT,
        reconciliation_status TEXT,
        created_at TEXT
    )
""")
conn.commit()
conn.close()
print("Execution ledger table created with all advisor-required fields")
