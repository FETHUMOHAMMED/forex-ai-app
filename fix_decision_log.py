with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the exact decision log line and add DB logging after it
# The line is: logger.info(f"[DECISION WATCH] {pair}: {inst_decision.decision_rationale}")
old_line = 'logger.info(f"[DECISION WATCH] {pair}: {inst_decision.decision_rationale}")'

new_block = '''logger.info(f"[DECISION WATCH] {pair}: {inst_decision.decision_rationale}")
            try:
                import sqlite3
                dc = sqlite3.connect("ai-service/trades.db")
                dc.execute("INSERT INTO decision_memory (timestamp, pair, signal, confidence, grade, regime, decision, quality_score, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (datetime.now(timezone.utc).isoformat(), pair, signal.get("signal","UNKNOWN"), signal.get("confidence",0), inst_decision.grade, signal.get("regime","UNKNOWN"), "WATCH", inst_decision.opportunity_score, inst_decision.decision_rationale))
                dc.commit()
                dc.close()
            except:
                pass'''

if old_line in content:
    content = content.replace(old_line, new_block)
    print("Added decision logging")
else:
    print("Line not found - searching...")
    for i, line in enumerate(content.split('\n')):
        if 'DECISION WATCH' in line:
            print(f"Line {i}: {line.strip()}")

with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)
