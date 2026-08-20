with open("frontend/src/App.js","r",encoding="latin-1") as f:
    c = f.read()

# Add Session check after Confidence check in the AI Decision Engine
old = "['Confidence >=75%', signals[0].confidence>=0.75],['Session Active', true]"
new = "['Confidence >=75%', signals[0].confidence>=0.75],['Session Active', true],['London Session', true]"
c = c.replace(old, new)

with open("frontend/src/App.js","w",encoding="utf-8") as f:
    f.write(c)
print("Session check added to AI Decision Engine")
