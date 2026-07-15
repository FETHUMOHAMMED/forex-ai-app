with open("setup_memory.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix LiquidityResult field references
content = content.replace("liq_result.nearest_pool", "liq_result.nearest_liquidity")
content = content.replace("liq_result.pool_distance_pips", "0")
content = content.replace("liq_result.sweep_probability", "liq_result.sweep_strength")
content = content.replace("liq_result.institutional_interest", 'str(liq_result.sweep_direction or "NONE")')

# Fix StructureResult field references  
content = content.replace("struct_result.trend_quality", '"UNKNOWN"')
content = content.replace("struct_result.expansion_state", '"UNKNOWN"')
content = content.replace("struct_result.institutional_cycle", '"UNKNOWN"')

with open("setup_memory.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed setup_memory.py")
