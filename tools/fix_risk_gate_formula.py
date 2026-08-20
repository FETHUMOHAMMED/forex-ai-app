"""Fix tick_value formula in order_boundary.py"""
path = 'packages/risk/order_boundary.py'
content = open(path).read()

# The bug: stop_distance_points * (tick_value / tick_size) * volume
# For 176 points, tick_value=1.0, tick_size=0.00001:
#   176 * (1.0 / 0.00001) * 0.01 = 176 * 100000 * 0.01 = 176,000 WRONG!
# 
# Correct: stop_distance_pips * pip_value_per_lot * volume
#   17.6 pips * $10/pip/lot * 0.01 = $1.76 CORRECT

old_formula = "actual_risk_amount = stop_distance_points * (symbol_tick_value / symbol_tick_size) * volume"
new_formula = """stop_distance_pips = stop_distance_points * symbol_point * 10
    pip_value_per_lot = (symbol_tick_value / symbol_tick_size) * symbol_point * 10
    actual_risk_amount = stop_distance_pips * pip_value_per_lot * volume"""

if old_formula in content:
    content = content.replace(old_formula, new_formula)
    open(path, 'w').write(content)
    print('FIXED: risk_per_lot formula in order_boundary.py')
else:
    print('Pattern not found - checking current formula:')
    import re
    matches = re.findall(r'actual_risk_amount.*', content)
    for m in matches[:3]:
        print(f'  {m.strip()[:100]}')
