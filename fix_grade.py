with open("institutional/trade_scorer.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '            result.recommendation = "SKIP"\n        else:\n            result.grade = "F"\n            result.recommendation = "SKIP"'
new = '            result.recommendation = "CAUTIOUS"\n        else:\n            result.grade = "F"\n            result.recommendation = "SKIP"'

if old in content:
    content = content.replace(old, new)
    print("FIXED: Grade D now = CAUTIOUS")
else:
    print("Pattern not found - file may already be fixed")
    for i, line in enumerate(content.split('\n')):
        if 'grade = "D"' in line:
            print(f"Line {i}: {line.strip()}")
            print(f"Line {i+1}: {content.split(chr(10))[i+1].strip()}")

with open("institutional/trade_scorer.py", "w", encoding="utf-8") as f:
    f.write(content)
