"""P0: Audit - How many places call mt5.order_send()?
Per advisor: There should be EXACTLY ONE order boundary.
"""
import re
from pathlib import Path

print("=" * 60)
print("  ORDER BOUNDARY AUDIT")
print("  Finding ALL mt5.order_send() call sites")
print("=" * 60)

# Find all Python files that call mt5.order_send
order_send_sites = []
for py_file in Path(".").rglob("*.py"):
    # Skip venv, node_modules, archive
    parts = set(py_file.parts)
    if parts & {'venv', 'node_modules', 'archive', '.venv', '__pycache__'}:
        continue
    
    try:
        content = py_file.read_text(encoding='utf-8', errors='ignore')
        for i, line in enumerate(content.split('\n'), 1):
            if 'order_send(' in line and 'mt5' in line.lower():
                order_send_sites.append((str(py_file), i, line.strip()))
    except:
        pass

print(f"\n  Found {len(order_send_sites)} direct mt5.order_send() call sites:")
print()

# Classify each site
for filepath, lineno, line in order_send_sites:
    if 'pipeline' in filepath.lower() or 'execution' in filepath.lower():
        category = "APPROVED (execution layer)"
    elif 'broker' in filepath.lower():
        category = "APPROVED (broker wrapper)"
    elif 'test' in filepath.lower() or 'test' in str(filepath):
        category = "TEST (not production path)"
    elif 'tool' in filepath.lower() or 'fix' in filepath.lower() or 'sync' in filepath.lower():
        category = "WARNING (tool/manual - should use pipeline)"
    else:
        category = "VIOLATION (bypasses pipeline)"
    
    print(f"  [{category}]")
    print(f"    {filepath}:{lineno}")
    print(f"    {line[:100]}")
    print()

# Recommendation
print("=" * 60)
print("  RECOMMENDED ARCHITECTURE:")
print("""
  EXACTLY ONE order boundary:
  
  packages/execution/execution_pipeline.py
      ?
  execute_pipeline(signal, ...)
      ?
  All 8 gates pass
      ?
  mt5.order_send()  ? THE ONLY CALL SITE
      ?
  Position verification
      ?
  DB persistence
  
  ALL other code must call execute_pipeline(), NOT mt5.order_send()
""")
print("=" * 60)
