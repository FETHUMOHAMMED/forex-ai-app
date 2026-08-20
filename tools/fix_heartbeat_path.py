# Fix heartbeat file path - needs to go up 3 levels from packages/observability/
path = 'packages/observability/heartbeat.py'
content = open(path).read()

# Fix: parent.parent is packages/, need parent.parent.parent for project root
old = 'root = Path(__file__).resolve().parent.parent'
new = 'root = Path(__file__).resolve().parent.parent.parent'

if old in content:
    content = content.replace(old, new)
    open(path, 'w').write(content)
    print('Fixed heartbeat root path')
else:
    print('Pattern not found')
