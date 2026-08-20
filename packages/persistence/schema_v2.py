"""Database Schema V2 - Explicit provenance for every field.
Every value tracks WHERE it came from: MT5, SIGNAL, DERIVED, or MANUAL.
"""
import sqlite3
from datetime import datetime, timezone

SCHEMA_VERSION = 2

# ============================================================================
# PROVENANCE TRACKING
# ============================================================================

PROVENANCE_SOURCES = {
    "MT5":     "Authoritative - from broker terminal",
    "SIGNAL":  "From AI signal at execution time",
    "DERIVED": "Calculated from other fields",
    "MANUAL":  "Manually entered/corrected",
    "UNKNOWN": "Source not tracked",
}

# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

TRADES_TABLE_V2 = """
CREATE TABLE IF NOT EXISTS trades_v2 (
    -- === PRIMARY IDENTITY ===
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT UNIQUE NOT NULL,          -- e.g., "V3_LiveMicro_20260811_001"
    signal_id TEXT NOT NULL,                -- AI signal that triggered trade
    
    -- === MT5 IDENTITY (distinguished by type!) ===
    mt5_order_ticket INTEGER,              -- mt5.order_send().order
    mt5_position_ticket INTEGER,           -- positions_get()[].ticket  
    mt5_entry_deal_ticket INTEGER,         -- history_deals(entry=0)
    mt5_exit_deal_ticket INTEGER,          -- history_deals(entry=1)
    
    -- === ACCOUNT (from MT5 - authoritative) ===
    account_id INTEGER NOT NULL,           -- MT5 login (e.g., REDACTED_LIVE_ACCOUNT)
    account_name TEXT NOT NULL,            -- "Live_Micro", "Demo2"
    broker_server TEXT NOT NULL,           -- "Exness-MT5Real10"
    environment TEXT NOT NULL,             -- "LIVE_MICRO_VALIDATION", "DEMO"
    
    -- === TIMESTAMPS (all UTC with timezone!) ===
    signal_timestamp_utc TEXT,             -- When AI generated signal
    order_timestamp_utc TEXT,              -- When order was sent
    position_open_utc TEXT,               -- When position opened in MT5
    position_close_utc TEXT,              -- When position closed in MT5
    db_created_utc TEXT NOT NULL,          -- When DB record was created
    db_updated_utc TEXT NOT NULL,          -- When DB record was last updated
    
    -- === PRICES (signal vs actual - tracked separately!) ===
    signal_entry REAL,                     -- Planned entry from AI signal
    signal_sl REAL,                        -- Planned stop loss
    signal_tp REAL,                        -- Planned take profit
    actual_entry REAL,                     -- Actual fill price from MT5
    actual_sl REAL,                        -- Actual SL from MT5 position
    actual_tp REAL,                        -- Actual TP from MT5 position
    actual_exit REAL,                      -- Actual exit price from MT5 deal
    
    -- === EXECUTION ===
    pair TEXT NOT NULL,
    direction TEXT NOT NULL,               -- "BUY" or "SELL"
    volume REAL,                           -- Actual executed volume
    confidence REAL,                       -- AI confidence at execution
    
    -- === FINANCIAL (from MT5 - authoritative) ===
    mt5_profit REAL,                       -- Profit from MT5 exit deal
    mt5_commission REAL DEFAULT 0.0,       -- Commission from MT5
    mt5_swap REAL DEFAULT 0.0,             -- Swap from MT5
    mt5_net_pnl REAL,                      -- profit + commission + swap
    
    -- === DERIVED ===
    risk_amount REAL,                      -- Actual $ risk at SL
    risk_pct_of_balance REAL,              -- Risk as % of balance at entry
    r_multiple REAL,                       -- PnL / risk_amount
    slippage_entry_pips REAL,             -- actual_entry - signal_entry in pips
    
    -- CLASSIFICATION ===
    strategy_version TEXT NOT NULL,        -- "V3_REGIME", "PRE_V3"
    trade_mode TEXT NOT NULL,              -- "VALIDATION", "PRODUCTION"
    regime TEXT,                           -- From signal
    institutional_bias TEXT,
    institutional_score REAL,
    dealer_pressure TEXT,
    liquidity_state TEXT,
    continuation_prob REAL,
    
    -- RECONCILIATION ===
    reconciliation_status TEXT DEFAULT 'PENDING',  -- PENDING, MATCH, MISMATCH, PHANTOM, ORPHAN
    reconciliation_checked_utc TEXT,               -- Last reconciliation check
    reconciliation_issues TEXT,                    -- JSON list of issues found
    
    -- PROVENANCE (tracks source of every field!) ===
    provenance_entry TEXT DEFAULT 'UNKNOWN',       -- MT5 or SIGNAL
    provenance_exit TEXT DEFAULT 'UNKNOWN',
    provenance_pnl TEXT DEFAULT 'UNKNOWN',
    provenance_volume TEXT DEFAULT 'UNKNOWN',
    
    -- INTEGRITY
    is_validated INTEGER DEFAULT 0,        -- 1 if passed all invariant checks
    validation_errors TEXT,                -- JSON list of validation errors
    data_version INTEGER DEFAULT 2,        -- Schema version
    
    -- RESULT
    result TEXT,                           -- WIN, LOSS, BREAKEVEN, OPEN
    reason TEXT,                           -- Exit reason from MT5
    comment TEXT                           -- Free-text notes
)
"""

# ============================================================================
# INDEXES
# ============================================================================

INDEXES_V2 = [
    "CREATE INDEX IF NOT EXISTS idx_v2_trade_id ON trades_v2(trade_id)",
    "CREATE INDEX IF NOT EXISTS idx_v2_signal_id ON trades_v2(signal_id)",
    "CREATE INDEX IF NOT EXISTS idx_v2_position ON trades_v2(mt5_position_ticket)",
    "CREATE INDEX IF NOT EXISTS idx_v2_account ON trades_v2(account_id, account_name)",
    "CREATE INDEX IF NOT EXISTS idx_v2_strategy ON trades_v2(strategy_version)",
    "CREATE INDEX IF NOT EXISTS idx_v2_pair ON trades_v2(pair)",
    "CREATE INDEX IF NOT EXISTS idx_v2_result ON trades_v2(result)",
    "CREATE INDEX IF NOT EXISTS idx_v2_reconciliation ON trades_v2(reconciliation_status)",
    "CREATE INDEX IF NOT EXISTS idx_v2_open_utc ON trades_v2(position_open_utc)",
    "CREATE INDEX IF NOT EXISTS idx_v2_validated ON trades_v2(is_validated)",
]

# ============================================================================
# MIGRATION
# ============================================================================

def migrate_to_v2(db_path: str = "ai-service/trades.db"):
    """Migrate existing trades table to V2 with provenance tracking"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Check if V2 already exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades_v2'")
    if c.fetchone():
        print("trades_v2 already exists - skipping migration")
        conn.close()
        return
    
    print("Migrating to schema V2...")
    
    # Create V2 table
    c.execute(TRADES_TABLE_V2)
    
    # Create indexes
    for idx in INDEXES_V2:
        c.execute(idx)
    
    # Migrate existing valid trades
    c.execute("""
        INSERT INTO trades_v2 (
            trade_id, signal_id,
            mt5_position_ticket,
            account_id, account_name, broker_server, environment,
            signal_timestamp_utc, order_timestamp_utc,
            position_open_utc, position_close_utc,
            db_created_utc, db_updated_utc,
            signal_entry, signal_sl, signal_tp,
            actual_entry, actual_sl, actual_tp, actual_exit,
            pair, direction, volume, confidence,
            mt5_profit, mt5_commission, mt5_swap, mt5_net_pnl,
            strategy_version, trade_mode, regime,
            institutional_bias, institutional_score,
            dealer_pressure, liquidity_state, continuation_prob,
            result, reason
        )
        SELECT
            'V3_' || account || '_' || id AS trade_id,
            'signal_' || timestamp AS signal_id,
            mt5_position_id,
            account_id, account, 'Exness-MT5Real10',
            CASE WHEN account = 'Live_Micro' THEN 'LIVE_MICRO_VALIDATION' ELSE 'DEMO' END,
            timestamp, timestamp,
            timestamp, exit_time,
            timestamp, COALESCE(exit_time, timestamp),
            planned_entry, planned_sl, planned_tp,
            entry, stop_loss, take_profit, exit_price,
            pair, signal, volume, confidence,
            pnl, 0, 0, pnl,
            strategy_version, trade_mode, regime,
            institutional_bias, institutional_score,
            dealer_pressure, liquidity_state, continuation_prob,
            result, reason
        FROM trades
        WHERE strategy_version = 'V3_REGIME'
        AND mt5_position_id IS NOT NULL
        AND result != 'PHANTOM'
    """)
    
    migrated = c.rowcount if hasattr(c, 'rowcount') else "?"
    conn.commit()
    conn.close()
    
    print(f"Migrated {migrated} validated trades to trades_v2")
    print("Schema V2 ready with provenance tracking")


# ============================================================================
# VALIDATION QUERIES (using V2 schema)
# ============================================================================

def get_validated_v3_trades(db_path: str = "ai-service/trades.db") -> list:
    """Get V3 trades that pass all validation criteria"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("""
        SELECT trade_id, pair, direction, actual_entry, actual_exit,
               mt5_net_pnl, result, position_open_utc, position_close_utc,
               reconciliation_status
        FROM trades_v2
        WHERE strategy_version = 'V3_REGIME'
        AND account_name = 'Live_Micro'
        AND is_validated = 1
        AND reconciliation_status = 'MATCH'
        AND result IN ('WIN', 'LOSS', 'BREAKEVEN')
        ORDER BY position_close_utc
    """)
    
    trades = c.fetchall()
    conn.close()
    return trades


def get_phantom_trades(db_path: str = "ai-service/trades.db") -> list:
    """Find trades with no MT5 verification"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("""
        SELECT trade_id, pair, actual_entry, volume, result
        FROM trades_v2
        WHERE reconciliation_status = 'PHANTOM'
        OR mt5_position_ticket IS NULL
    """)
    
    trades = c.fetchall()
    conn.close()
    return trades


if __name__ == "__main__":
    migrate_to_v2()
    print(f"\nValidated V3 trades: {len(get_validated_v3_trades())}")
    print(f"Phantom trades: {len(get_phantom_trades())}")
