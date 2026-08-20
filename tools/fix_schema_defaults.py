import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

print("Current defaults (from schema):")
for col in ['account_name', 'strategy_version', 'trade_mode', 'environment']:
    c.execute(f"SELECT dflt_value FROM pragma_table_info('trades') WHERE name='{col}'")
    row = c.fetchone()
    print(f"  {col}: {row[0] if row else 'no default'}")

# Drop the old trigger
c.execute('DROP TRIGGER IF EXISTS set_v3_strategy')
print('Dropped old PRE_V3->V3_REGIME trigger')

# Create better trigger
c.execute('''
    CREATE TRIGGER IF NOT EXISTS enforce_v3_defaults
    AFTER INSERT ON trades
BEGIN
    UPDATE trades SET 
        strategy_version = CASE WHEN NEW.strategy_version IS NULL OR NEW.strategy_version = 'PRE_V3' 
                                THEN 'V3_REGIME' ELSE NEW.strategy_version END,
        trade_mode = CASE WHEN NEW.trade_mode IS NULL OR NEW.trade_mode = 'PRODUCTION'
                          THEN 'VALIDATION' ELSE NEW.trade_mode END
    WHERE id = NEW.id;
END
''')
print('Created enforce_v3_defaults trigger')

conn.commit()
conn.close()
print('Done - new trades will have correct defaults')
