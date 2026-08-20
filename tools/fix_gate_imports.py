# Add sys.path to the integrity gate
path = 'packages/observability/system_integrity_gate.py'
content = open(path).read()

# Add sys.path after imports
if 'sys.path.insert' not in content:
    content = content.replace(
        'import sqlite3',
        'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))\nimport sqlite3'
    )
    open(path, 'w').write(content)
    print('Fixed sys.path in system_integrity_gate.py')
else:
    print('sys.path already present')
