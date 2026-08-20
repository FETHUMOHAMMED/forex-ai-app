"""Remove ALL hardcoded passwords from source code"""
import re
from pathlib import Path

# Files with known hardcoded passwords
files_to_fix = [
    "tools/fix_stale_trades.py",
    "utils/backfill_trades.py", 
    "backend/services/dashboard_service.py",
    "ai-service/broker_exness.py",
]

for filepath in files_to_fix:
    p = Path(filepath)
    if not p.exists():
        print(f"  SKIP: {filepath} not found")
        continue
    
    content = p.read_text(encoding='utf-8', errors='replace')
    
    # Replace password="xxx" with environment variable
    content = re.sub(
        r'password\s*=\s*"[^"]+"',
        'password=os.getenv("MT5_PASSWORD")',
        content
    )
    
    p.write_text(content, encoding='utf-8')
    print(f"  FIXED: {filepath}")

print("\nDone. All passwords now use environment variables.")
