# -*- coding: utf-8 -*-
"""Normalized Event Schema - Separate tables for each entity type."""
import sqlite3

def create_normalized_schema(db_path="ai-service/trades.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            signal_id TEXT PRIMARY KEY,
            pair TEXT NOT NULL,
            direction TEXT NOT NULL,
            confidence REAL NOT NULL,
            planned_entry REAL NOT NULL,
            planned_sl REAL NOT NULL,
            planned_tp REAL NOT NULL,
            regime TEXT,
            generated_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            strategy_version TEXT NOT NULL,
            model_version TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL REFERENCES signals(signal_id),
            account_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            environment TEXT NOT NULL,
            order_type TEXT NOT NULL,
            requested_volume REAL NOT NULL,
            requested_entry REAL,
            requested_sl REAL,
            requested_tp REAL,
            submitted_at TEXT,
            mt5_order_ticket INTEGER,
            mt5_retcode INTEGER,
            mt5_comment TEXT,
            status TEXT NOT NULL DEFAULT 'CREATED'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            position_ticket INTEGER PRIMARY KEY,
            order_id TEXT REFERENCES orders(order_id),
            account_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            volume REAL NOT NULL,
            entry_price REAL NOT NULL,
            sl REAL,
            tp REAL,
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            deal_ticket INTEGER PRIMARY KEY,
            position_ticket INTEGER NOT NULL REFERENCES positions(position_ticket),
            entry_type INTEGER NOT NULL,
            price REAL NOT NULL,
            volume REAL NOT NULL,
            profit REAL,
            commission REAL DEFAULT 0,
            swap REAL DEFAULT 0,
            deal_time TEXT NOT NULL
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades_normalized (
            trade_id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            position_ticket INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            environment TEXT NOT NULL,
            strategy_version TEXT NOT NULL,
            pair TEXT NOT NULL,
            direction TEXT NOT NULL,
            confidence REAL,
            planned_entry REAL,
            actual_entry REAL,
            planned_sl REAL,
            actual_sl REAL,
            planned_tp REAL,
            actual_tp REAL,
            volume REAL,
            pnl REAL,
            entry_deviation_pips REAL,
            result TEXT,
            opened_at TEXT,
            closed_at TEXT,
            is_qualified INTEGER DEFAULT 0,
            qualification_reason TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("Normalized schema created: signals, orders, positions, deals, trades_normalized")

if __name__ == "__main__":
    create_normalized_schema()
    
    conn = sqlite3.connect('ai-service/trades.db')
    c = conn.cursor()
    tables = ["signals", "orders", "positions", "deals", "trades_normalized"]
    print("\n  NORMALIZED TABLES:")
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
        exists = c.fetchone()[0] > 0
        print(f"    {table}: {'EXISTS' if exists else 'MISSING'}")
    conn.close()
    
    print("\n  ENTITY RELATIONSHIP:")
    print("    signals -> orders -> positions -> deals")
    print("    trades_normalized = materialized view")
