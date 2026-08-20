with open("ai-service/auto_trader_exness.py","r",encoding="latin-1") as f:
    content = f.read()

old = 'print(f"[DUPLICATE REJECT] {pair}'
new = '''now_ts = datetime.now(timezone.utc).timestamp()
last_dup = getattr(self, '_last_dup_log', {})
pair_key = f'{acc.name}_{pair}_{existing_direction}'
if pair_key not in last_dup or now_ts - last_dup[pair_key] > 60:
    print(f"[DUPLICATE REJECT] {pair}'''

if old in content:
    content = content.replace(old, new)
    print("Throttled duplicate rejection")
else:
    print("Pattern not found")

with open("ai-service/auto_trader_exness.py","w",encoding="latin-1") as f:
    f.write(content)
