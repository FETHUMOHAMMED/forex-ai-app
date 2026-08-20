import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

if not mt5.initialize():
    print("MT5 not running")
    exit()

# Connect to the active demo account (Demo2)
mt5.login(REDACTED_DEMO_ACCOUNT, password=os.getenv("MT5_PASSWORD"), server="Exness-MT5Trial9")

db = sqlite3.connect("trades.db")
cursor = db.cursor()

# Ensure required columns exist
for col in [("ticket", "INTEGER"), ("exit_time", "TEXT"), ("pnl", "REAL"), ("exit_price", "REAL")]:
    try:
        cursor.execute(f"ALTER TABLE trades ADD COLUMN {col[0]} {col[1]}")
    except:
        pass
db.commit()

# Fetch all closed deals from MT5 history (past few months)
from_date = datetime(2026, 1, 1)
to_date = datetime.now()
deals = mt5.history_deals_get(from_date, to_date)

if deals is None or len(deals) == 0:
    print("No closed deals found in MT5 history.")
    exit()

updated = 0
for deal in deals:
    if deal.entry == 1:   # DEAL_ENTRY_OUT
        ticket = deal.position_id
        exit_time = datetime.fromtimestamp(deal.time, tz=timezone.utc).isoformat()
        pnl = deal.profit
        exit_price = deal.price
        # Try to update an existing open trade with this ticket
        cursor.execute(
            "UPDATE trades SET exit_time=?, pnl=?, exit_price=? WHERE ticket=? AND exit_time IS NULL",
            (exit_time, pnl, exit_price, ticket)
        )
        if cursor.rowcount == 0:
            # No matching open trade – insert a minimal record
            cursor.execute(
                "INSERT INTO trades (ticket, pair, signal, timestamp, exit_time, pnl, exit_price) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticket, deal.symbol, 'UNKNOWN', exit_time, exit_time, pnl, exit_price)
            )
        updated += 1

db.commit()
db.close()
print(f"✅ Backfill complete. {updated} deals processed. Run analytics.py now.")