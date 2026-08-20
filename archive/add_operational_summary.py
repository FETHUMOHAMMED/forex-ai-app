with open("frontend/src/App.js","r",encoding="latin-1") as f:
    c = f.read()

# Add Operational Summary right after the header section, before the topRow grid
old = "{/* PRIORITY 1: PERFORMANCE (largest, top) */}"
new = """{/* OPERATIONAL SUMMARY */}
      <div style={{display:'flex',gap:'14px',flexWrap:'wrap',marginBottom:'8px',fontSize:'10px',color:'#94a3b8',background:'#1e293b',borderRadius:'6px',padding:'8px 12px',border:'1px solid #334155'}}>
        <span>?? Broker</span><span>?? Signal Server</span><span>?? MT5</span><span>?? AI Models (6)</span><span>?? Market Open</span><span>?? Trading: Waiting</span><span style={{color:'#64748b'}}>Outside London 07-11 UTC</span>
      </div>

{/* PRIORITY 1: PERFORMANCE (largest, top) */}"""
c = c.replace(old, new)

with open("frontend/src/App.js","w",encoding="utf-8") as f:
    f.write(c)
print("Operational Summary added at top")
