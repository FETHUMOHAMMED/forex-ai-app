import os

# Fix shadow_collector.py
with open("institutional/shadow_collector.py", "r", encoding="utf-8") as f:
    content = f.read()

old = 'def __init__(self, db_path: str = "ai-service/trades.db"):'
new = '''def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-service", "trades.db")'''

if old in content:
    content = content.replace(old, new)
    print("Fixed shadow_collector.py")
else:
    print("Pattern not found in shadow_collector.py")

with open("institutional/shadow_collector.py", "w", encoding="utf-8") as f:
    f.write(content)

# Fix strategy_memory.py
with open("institutional/strategy_memory.py", "r", encoding="utf-8") as f:
    content = f.read()

if old in content:
    content = content.replace(old, new)
    print("Fixed strategy_memory.py")
else:
    print("Pattern not found in strategy_memory.py")

with open("institutional/strategy_memory.py", "w", encoding="utf-8") as f:
    f.write(content)
