with open("institutional/trade_decision_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '        elif decision.opportunity_score >= 50:\n            return "WATCH"\n        return "REJECT"'
new = '        elif decision.opportunity_score >= 50:\n            return "REDUCE_SIZE"\n        elif decision.opportunity_score >= 40:\n            return "WATCH"\n        return "REJECT"'

if old in content:
    content = content.replace(old, new)
    print("FIXED: 50+ = REDUCE_SIZE, 40-49 = WATCH")
else:
    print("Pattern not found")

with open("institutional/trade_decision_engine.py", "w", encoding="utf-8") as f:
    f.write(content)
