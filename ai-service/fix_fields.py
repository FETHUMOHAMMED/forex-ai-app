with open("real_ai_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the crashing attribute: nearest_pool -> nearest_liquidity
content = content.replace("liq_result.nearest_pool", "liq_result.nearest_liquidity")

# Fix other old fields that don't exist on new LiquidityResult
content = content.replace("liq_result.pool_distance_pips", "0")
content = content.replace("liq_result.sweep_probability", "liq_result.sweep_strength")
content = content.replace("liq_result.institutional_interest", 'str(liq_result.sweep_direction or "NONE")')

with open("real_ai_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed 4 field references in real_ai_service.py")
