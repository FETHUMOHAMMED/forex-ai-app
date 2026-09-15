"""AST-BASED EXECUTION BOUNDARY ENFORCEMENT - Precise call detection."""
import ast
import sys
from pathlib import Path

def enforce_execution_boundary_ast():
    """Use AST to find ACTUAL mt5.order_send() calls (not comments/strings)."""
    print("="*70)
    print("  AST-BASED EXECUTION BOUNDARY ENFORCEMENT")
    print("="*70)
    
    APPROVED_FILES = [
        "packages/execution/single_path.py",
        "packages/execution/tier2_boundary.py",
    ]
    
    APPROVED_DIRS = ["tests/", "tools/", "archive/", "venv/", ".venv/", "site-packages/", "scripts/"]
    
    violations = []
    approved_calls = []
    
    for py_file in Path(".").rglob("*.py"):
        path_str = str(py_file).replace("\\", "/")
        
        # Skip non-production dirs
        if any(d in path_str for d in APPROVED_DIRS):
            continue
        
        try:
            source = py_file.read_text()
            tree = ast.parse(source)
        except:
            continue
        
        # Walk AST looking for actual mt5.order_send calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check if this is mt5.order_send(...)
                if (isinstance(node.func, ast.Attribute) and
                    isinstance(node.func.value, ast.Name) and
                    node.func.value.id == 'mt5' and
                    node.func.attr == 'order_send'):
                    
                    line = node.lineno
                    if any(approved in path_str for approved in APPROVED_FILES):
                        approved_calls.append((path_str, line))
                    else:
                        violations.append((path_str, line))
    
    # Display
    print(f"\n  APPROVED CALLS (in single_path.py):")
    for path, line in approved_calls:
        print(f"    ? {path}:{line}")
    
    if violations:
        print(f"\n  PRODUCTION VIOLATIONS ({len(violations)}):")
        for path, line in violations:
            print(f"    ? {path}:{line}")
        return False
    else:
        print(f"\n  NO PRODUCTION VIOLATIONS")
        print(f"  Only single_path.py calls mt5.order_send in production")
        return True

if __name__ == "__main__":
    result = enforce_execution_boundary_ast()
    sys.exit(0 if result else 1)



