with open("institutional/strategy_memory.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix: the real trades query selects 7 columns but _process_rows expects pair, regime, session, signal, pnl, score
# Change: institutional_bias -> institutional_bias as regime, and remove liquidity_state from SELECT
old = "SELECT pair, institutional_bias, liquidity_state, \n                     CASE"
new = "SELECT pair, institutional_bias as regime, \n                     CASE"
content = content.replace(old, new)

with open("institutional/strategy_memory.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed")
