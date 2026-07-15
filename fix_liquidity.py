with open("institutional/liquidity_intelligence.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "        self.liquidity_score = liquidity_score"
new = """        self.liquidity_score = liquidity_score
        # Compatibility aliases for old code
        self.nearest_pool = nearest_liquidity
        self.pool_distance_pips = 0
        self.sweep_probability = sweep_strength * 100 if sweep_strength else 0
        self.institutional_interest = sweep_direction or "NONE\""""

content = content.replace(old, new)

with open("institutional/liquidity_intelligence.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
