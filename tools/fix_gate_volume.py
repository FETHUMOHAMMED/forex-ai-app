# Fix SIZE gate to check signal volume
content = open('packages/integrity/execution/gate.py').read()
content = content.replace(
    '        volume = 0.01',
    '        volume = signal.get("volume", 0.01)'
)
open('packages/integrity/execution/gate.py', 'w').write(content)
print('SIZE gate now checks signal volume')
