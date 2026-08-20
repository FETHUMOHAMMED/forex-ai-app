# Fix the stray "<" on line 383
lines = open('frontend/src/App.js').readlines()
fixed = []
for i, line in enumerate(lines):
    # Line 383 has a stray "<" before the comment
    if i == 382 and line.strip() == '<':
        continue  # Skip the stray character
    fixed.append(line)
open('frontend/src/App.js', 'w').writelines(fixed)
print('Fixed stray < on line 383')
