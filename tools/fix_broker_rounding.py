"""Fix broker_exness.py to round SL/TP to symbol digits before sending"""
import sys
from pathlib import Path

broker_path = Path("ai-service/broker_exness.py")

with open(broker_path, 'r') as f:
    content = f.read()

# Find the order request construction and add rounding
old_code = '''            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": request_type,
                "price": price,
                "sl": sl,
                "tp": tp,'''

new_code = '''            # Normalize prices to symbol digits to avoid "Invalid stops" error
            digits = symbol_info.digits if symbol_info else 5
            sl = round(sl, digits)
            tp = round(tp, digits)
            price = round(price, digits)

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": request_type,
                "price": price,
                "sl": sl,
                "tp": tp,'''

if old_code in content:
    content = content.replace(old_code, new_code)
    
    # Backup
    import shutil
    shutil.copy2(broker_path, broker_path.with_suffix('.py.bak'))
    
    with open(broker_path, 'w') as f:
        f.write(content)
    
    print("Fixed broker_exness.py - added price normalization")
    print("SL/TP/price are now rounded to symbol digits before order")
    print("Daemon restart required for fix to take effect")
else:
    print("Could not find the exact code pattern to replace")
    print("Check the broker_exness.py manually around the order request")
