with open("frontend/src/App.js","r",encoding="latin-1") as f:
    c = f.read()

# Add Market Status panel after Account Health card
old = "{/* PRIORITY 3: RESEARCH + MILESTONES */}"
new = """{/* MARKET STATUS */}
      <div style={{...topRow,marginTop:'12px'}}>
        <Card>
          <Title text="MARKET STATUS"/>
          <Row label="Market" value="?? Open"/>
          <Row label="Current Session" value="London"/>
          <Row label="Trading Window" value="?? Closed"/>
          <Row label="Reason" value="Outside London (07-11 UTC)"/>
          <Row label="Next Window" value="07:00 UTC"/>
          <Row label="Active Pairs" value="EURUSD only"/>
          <Row label="Regime Filter" value="BREAKOUT+DISTRIBUTING"/>
        </Card>
      </div>

{/* PRIORITY 3: RESEARCH + MILESTONES */}"""
c = c.replace(old, new)

with open("frontend/src/App.js","w",encoding="utf-8") as f:
    f.write(c)
print("Market Status panel added")
