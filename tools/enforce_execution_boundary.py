"""ENFORCE EXECUTION BOUNDARY - Fail if order_send outside approved path."""
import sys
from pathlib import Path

def enforce_execution_boundary():
    """Verify ONLY approved files can call mt5.order_send."""
    print("="*70)
    print("  EXECUTION BOUNDARY ENFORCEMENT")
    print("="*70)
    
    # APPROVED files (only these can call order_send)
    APPROVED_FILES = [
        "packages/execution/single_path.py",
    ]
    
    # APPROVED directories (tests, tools allowed for diagnostics)
    APPROVED_DIRS = [
        "tests/",
        "tools/",
        "archive/",
        "scripts/",
        "archive/",
        "venv/",
        ".venv/",
        "site-packages/",
    ]
    
    violations = []
    
    # Scan all Python files
    for py_file in Path(".").rglob("*.py"):
        path_str = str(py_file)
        
        # Skip approved dirs
        if any(d in path_str for d in APPROVED_DIRS):
            continue
        
        # Read file
        try:
            content = py_file.read_text()
        except:
            continue
        
        # Check for actual order_send calls (not comments)
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if 'mt5.order_send' in stripped and not stripped.startswith('#'):
                # Check if file is approved
                if not any(approved in path_str for approved in APPROVED_FILES):
                    violations.append((path_str, i, stripped))
    
    # Display results
    if violations:
        print(f"\n  ? VIOLATIONS FOUND ({len(violations)}):")
        for path, line, code in violations:
            print(f"    {path}:{line}: {code}")
        print(f"\n  Only these files may call mt5.order_send:")
        for approved in APPROVED_FILES:
            print(f"    ? {approved}")
        return False
    else:
        print(f"\n  ? NO VIOLATIONS")
        print(f"  Only approved files call mt5.order_send:")
        for approved in APPROVED_FILES:
            print(f"    ? {approved}")
        return True

if __name__ == "__main__":
    result = enforce_execution_boundary()
    sys.exit(0 if result else 1)

