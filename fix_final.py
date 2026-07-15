with open("institutional/strategy_memory.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the entire _process_rows INSERT block with a simpler version
old_block = """        # Upsert
            c.execute('''INSERT INTO strategy_memory 
                (pair, regime, session, signal, trades, wins, win_rate, avg_pnl, total_pnl, avg_score, last_updated)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pair, regime, session, signal) DO UPDATE SET
                trades = trades + 1,
                wins = wins + ?,
                win_rate = ROUND(CAST(wins + ? AS REAL) / (trades + 1) * 100, 1),
                avg_pnl = ROUND((total_pnl + ?) / (trades + 1), 2),
                total_pnl = total_pnl + ?,
                avg_score = ROUND((avg_score * trades + ?) / (trades + 1), 1),
                last_updated = ?''',
                (pair, regime, session, signal, win, pnl, score, now,
                 win, win, pnl, pnl, score, now))"""

new_block = """        # Upsert using simpler approach
            c.execute("SELECT id, trades, wins, total_pnl, avg_score FROM strategy_memory WHERE pair=? AND regime=? AND session=? AND signal=?", 
                     (pair, regime, session, signal))
            existing = c.fetchone()
            
            if existing:
                new_trades = existing[1] + 1
                new_wins = existing[2] + win
                new_total_pnl = (existing[3] or 0) + pnl
                new_avg_score = ((existing[4] or 0) * existing[1] + score) / new_trades
                new_wr = round(new_wins / new_trades * 100, 1)
                new_avg_pnl = round(new_total_pnl / new_trades, 2)
                
                c.execute("UPDATE strategy_memory SET trades=?, wins=?, win_rate=?, avg_pnl=?, total_pnl=?, avg_score=?, last_updated=? WHERE id=?",
                         (new_trades, new_wins, new_wr, new_avg_pnl, new_total_pnl, new_avg_score, now, existing[0]))
            else:
                c.execute("INSERT INTO strategy_memory (pair, regime, session, signal, trades, wins, win_rate, avg_pnl, total_pnl, avg_score, last_updated) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)",
                         (pair, regime, session, signal, win, round(win*100, 1), pnl, pnl, score, now))"""

content = content.replace(old_block, new_block)

with open("institutional/strategy_memory.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed - replaced with simple SELECT/UPDATE/INSERT logic")
