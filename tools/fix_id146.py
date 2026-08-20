import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

# ID 146 is a phantom trade - clear the fake exit data
c.execute("""
    UPDATE trades SET 
        exit_time = NULL,
        exit_price = NULL,
        pnl = NULL,
        result = 'LEGACY_INVALID_PHANTOM'
    WHERE id = 146
""")
conn.commit()
print("Fixed ID 146 - cleared fake exit data. It is a PHANTOM trade (never executed in MT5)")
conn.close()
