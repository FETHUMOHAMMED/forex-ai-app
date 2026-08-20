content = open('tools/qualified_trade_check.py').read()
if 'sys.path.insert' not in content:
    content = content.replace(
        'import sqlite3',
        'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent))\nimport sqlite3'
    )
    open('tools/qualified_trade_check.py', 'w').write(content)
    print('Added sys.path to checker')
else:
    print('sys.path already present')
