with open("institutional/shadow_simulator.py", "r", encoding="utf-8") as f:
    content = f.read()

# The line has escaped quotes - fix them
old = 'stats[\\"missed_wins\\"]'
new = 'stats["missed_wins"]'
content = content.replace(old, new)

old = 'stats[\\"missed_pnl\\"]'
new = 'stats["missed_pnl"]'
content = content.replace(old, new)

old = 'stats[\\"correct_rejections\\"]'
new = 'stats["correct_rejections"]'
content = content.replace(old, new)

old = 'stats[\\"saved_loss\\"]'
new = 'stats["saved_loss"]'
content = content.replace(old, new)

with open("institutional/shadow_simulator.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed shadow_simulator.py")
