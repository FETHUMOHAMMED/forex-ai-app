"""Sync the orphan MT5 position (589629837) into the database"""
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timezone

mt5.initialize()
positions = mt5.positions_get()

if positions:
    for p in positions:
        if p.ticket == 589629837:
            conn = sqlite3.connect('ai-service/trades.db')
            c = conn.cursor()
            
            # Check if already in DB
            c.execute("SELECT id FROM trades WHERE ticket = ?", (p.ticket,))
            if not c.fetchone():
                direction = 'SELL' if p.type == 1 else 'BUY'
                now_utc = datetime.now(timezone.utc).isoformat()
                
                c.execute("""
                    INSERT INTO trades 
                    (timestamp, pair, signal, confidence, entry, stop_loss, take_profit,
                     volume, ticket, regime, account, account_name, account_id,
                     environment, strategy_version, trade_mode, mt5_position_id,
                     institutional_bias, institutional_score, dealer_pressure, 
                     liquidity_state, continuation_prob)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    now_utc, p.symbol.replace('m', ''), direction, 0.83,
                    p.price_open, p.sl if p.sl else p.price_open * 1.0015, 
                    p.tp if p.tp else p.price_open * 0.9985,
                    p.volume, p.ticket, 'volatile', 'Live_Micro', 'Live_Micro', REDACTED_LIVE_ACCOUNT,
                    'LIVE_MICRO_VALIDATION', 'V3_REGIME', 'VALIDATION', p.ticket,
                    'BREAKOUT', 81.85, 'SELLING_PRESSURE', 'SWEEP_SELL', 0.5
                ))
                conn.commit()
                print(f"Added orphan position {p.ticket} to database")
                print(f"  Symbol: {p.symbol} | Direction: {direction} | Volume: {p.volume}")
                print(f"  Entry: {p.price_open} | Current: {p.price_current} | Profit: ${p.profit:.2f}")
            else:
                print(f"Position {p.ticket} already in database")
            
            conn.close()
            break

mt5.shutdown()
