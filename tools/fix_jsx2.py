content = open('frontend/src/App.js').read()

# Fix the broken V3Performance line
content = content.replace(
    '          V3Performance data={v3Data.performance} />',
    '          <V3Performance data={v3Data.performance} />'
)

open('frontend/src/App.js', 'w').write(content)
print('Fixed V3Performance opening tag')
