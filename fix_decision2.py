with open("institutional/trade_decision_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '        elif decision.opportunity_score >= 50:\n            return "REDUCE_SIZE"\n        elif decision.opportunity_score >= 40:\n            return "WATCH"\n        return "REJECT"'
new = '        elif decision.opportunity_score >= 40:\n            return "REDUCE_SIZE"\n        elif decision.opportunity_score >= 30:\n            return "WATCH"\n        return "REJECT"'

if old in content:
    content = content.replace(old, new)
    print("FIXED: 40+ = REDUCE_SIZE, 30-39 = WATCH")
else:
    print("Pattern not found - checking...")
    for i, line in enumerate(content.split('\n')):
        if 'REDUCE_SIZE' in line or 'WATCH' in line:
            print(f"  Line {i}: {line.strip()}")

with open("institutional/trade_decision_engine.py", "w", encoding="utf-8") as f:
    f.write(content)
