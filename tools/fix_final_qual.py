# Fix the len() bug
path = 'packages/execution/final_qualification_engine.py'
content = open(path).read()
content = content.replace("print(f\"  Failed: {len(result['failed_count'])} gates\")", 
                          "print(f\"  Failed: {result['failed_count']} gates\")")
open(path, 'w').write(content)
print('Fixed')
