import json
with open("ai-service/config.json") as f:
    c = json.load(f)
for a in c["accounts"]:
    if a["name"] == "Demo2":
        a["pairs"] = ["EURUSD"]
        a["sessions_enabled"] = ["LONDON"]
        print("EURUSD only, London only")
with open("ai-service/config.json","w") as f:
    json.dump(c, f, indent=2)
