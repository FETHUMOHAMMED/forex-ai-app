with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add decision logging right after the decision is made
old = """logger.info(f"[DECISION WATCH] {pair}: Marginal setup (Grade {grade}) - monitor for improvement")"""
new = """logger.info(f"[DECISION WATCH] {pair}: Marginal setup (Grade {grade}) - monitor for improvement")
            # Log decision to decision_memory
            try:
                import sqlite3
                dc = sqlite3.connect('ai-service/trades.db')
                dc.execute('''INSERT INTO decision_memory (timestamp, pair, signal, confidence, grade, regime, decision, quality_score, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (datetime.now(timezone.utc).isoformat(), pair, signal.get('signal','UNKNOWN'), signal.get('confidence',0), grade, signal.get('regime','UNKNOWN'), 'WATCH', score, 'Marginal setup'))
                dc.commit()
                dc.close()
            except: pass"""

if old in content:
    content = content.replace(old, new)
    print("Added decision logging for WATCH")
else:
    print("WATCH pattern not found, trying other patterns...")
    for line in content.split('\n'):
        if 'DECISION' in line and 'logger' in line:
            print(line)

with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)
