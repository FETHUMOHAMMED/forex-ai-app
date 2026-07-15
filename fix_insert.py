with open("institutional/strategy_memory.py", "r", encoding="utf-8") as f:
    content = f.read()

# The INSERT has 16 ? placeholders but only 14 values. 
# Remove avg_confidence from INSERT (it's always 0 for now)
old = """(pair, regime, session, signal, trades, wins, win_rate, avg_pnl, total_pnl, avg_confidence, avg_score, last_updated)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, 0, ?, ?)"""
new = """(pair, regime, session, signal, trades, wins, win_rate, avg_pnl, total_pnl, avg_score, last_updated)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)"""
content = content.replace(old, new)

with open("institutional/strategy_memory.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed INSERT - now 11 columns, 11 values")
