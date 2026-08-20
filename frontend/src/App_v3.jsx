import React, { useState, useEffect } from 'react';

function App() {
  const [signals, setSignals] = useState([]);
  const [connected, setConnected] = useState(false);
  const [v3Data, setV3Data] = useState(null);

  useEffect(() => {
    // Fetch V3 dashboard data
    const fetchV3 = async () => {
      try {
        const res = await fetch('http://localhost:8002/v3/dashboard');
        const data = await res.json();
        setV3Data(data);
      } catch(e) { console.log('V3 API connecting...'); }
    };
    fetchV3();
    const interval = setInterval(fetchV3, 15000);
    
    // WebSocket for signals
    const ws = new WebSocket('ws://localhost:8080?token=REDACTED_WS_TOKEN');
    ws.onopen = () => setConnected(true);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'signals') setSignals(data.data || []);
      } catch(e) {}
    };
    ws.onclose = () => setConnected(false);
    
    return () => { clearInterval(interval); ws.close(); };
  }, []);

  const p = v3Data?.performance || {};
  const arch = v3Data?.archive || {};
  const t = p.trades || 0;
  const progressPct = Math.min(100, (t/100)*100);

  return (
    <div style={{background:'#0f172a',minHeight:'100vh',color:'#e2e8f0',fontFamily:'monospace',padding:'20px'}}>
      
      {/* HEADER */}
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'20px',borderBottom:'1px solid #334155',paddingBottom:'10px'}}>
        <div>
          <h1 style={{fontSize:'24px',fontWeight:'bold',color:'#38bdf8'}}>FOREX-AI-APP</h1>
          <p style={{color:'#94a3b8',fontSize:'14px'}}>V3_REGIME Institutional AI Trading System</p>
        </div>
        <div style={{display:'flex',alignItems:'center',gap:'8px'}}>
          <span style={{width:'10px',height:'10px',borderRadius:'50%',background:connected?'#22c55e':'#ef4444',display:'inline-block'}}></span>
          <span style={{color:connected?'#22c55e':'#ef4444',fontSize:'14px'}}>{connected?'LIVE CONNECTED':'OFFLINE'}</span>
        </div>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:'16px'}}>

        {/* 1. V3 VALIDATION + PERFORMANCE */}
        <div style={{background:'#1e293b',borderRadius:'8px',padding:'16px',border:'1px solid #334155'}}>
          <h2 style={{color:'#38bdf8',fontSize:'16px',marginBottom:'12px'}}>V3 VALIDATION</h2>
          <div style={{background:'#334155',borderRadius:'4px',height:'20px',marginBottom:'8px'}}>
            <div style={{background:'#38bdf8',width:progressPct+'%',height:'100%',borderRadius:'4px',transition:'width 0.5s'}}></div>
          </div>
          <p style={{fontSize:'24px',fontWeight:'bold'}}>{t} <span style={{fontSize:'14px',color:'#94a3b8'}}>/ 100 Trades</span></p>
          <p style={{color:'#94a3b8',fontSize:'12px'}}>Stage: Micro Validation</p>
          
          <div style={{marginTop:'16px',borderTop:'1px solid #334155',paddingTop:'12px'}}>
            <h3 style={{color:'#94a3b8',fontSize:'13px',marginBottom:'8px'}}>PERFORMANCE</h3>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'8px',fontSize:'13px'}}>
              <div>Trades: <b>{t}</b></div>
              <div>Win Rate: <b>{t>=10 ? p.win_rate+'%' : 'N/A'}</b></div>
              <div>PF: <b>{p.profit_factor || 'N/A'}</b></div>
              <div>P&L: <b style={{color:p.pnl>=0?'#22c55e':'#ef4444'}}>${p.pnl||0}</b></div>
            </div>
          </div>

          {/* 4. RESEARCH MILESTONES */}
          <div style={{marginTop:'16px',borderTop:'1px solid #334155',paddingTop:'12px'}}>
            <h3 style={{color:'#94a3b8',fontSize:'13px',marginBottom:'8px'}}>MILESTONES</h3>
            {[10,25,50,100,300].map(m => (
              <div key={m} style={{fontSize:'12px',marginBottom:'4px',color:t>=m?'#22c55e':'#64748b'}}>
                {t>=m?'?':'?'} {m} trades: {m===10?'Execution verified':m===25?'Risk verified':m===50?'Initial review':m===100?'Statistical validation':'Production ready'}
              </div>
            ))}
          </div>
        </div>

        {/* 2. CURRENT AI SIGNALS (with institutional info) */}
        <div style={{background:'#1e293b',borderRadius:'8px',padding:'16px',border:'1px solid #334155'}}>
          <h2 style={{color:'#38bdf8',fontSize:'16px',marginBottom:'12px'}}>CURRENT AI SIGNALS</h2>
          {signals.length === 0 && <p style={{color:'#64748b'}}>No active signals</p>}
          {signals.map((s,i) => (
            <div key={i} style={{background:'#0f172a',borderRadius:'6px',padding:'12px',marginBottom:'8px',border:'1px solid #334155'}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                <span style={{fontWeight:'bold',fontSize:'18px',color:s.signal==='SELL'?'#ef4444':'#22c55e'}}>{s.pair} {s.signal}</span>
                <span style={{background:s.confidence>=0.75?'#22c55e':'#eab308',color:'#000',padding:'2px 8px',borderRadius:'4px',fontSize:'12px',fontWeight:'bold'}}>{(s.confidence*100).toFixed(0)}%</span>
              </div>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'4px',marginTop:'8px',fontSize:'12px',color:'#94a3b8'}}>
                <div>Regime: <b style={{color:'#e2e8f0'}}>{s.institutional_bias||'?'}</b></div>
                <div>Dealer: <b style={{color:'#e2e8f0'}}>{s.dealer_pressure||'?'}</b></div>
                <div>Liquidity: <b style={{color:'#e2e8f0'}}>{s.liquidity_state||'?'}</b></div>
                <div>Session: <b style={{color:'#e2e8f0'}}>{s.session||'London'}</b></div>
              </div>
              <div style={{marginTop:'8px',fontSize:'11px',color:'#64748b'}}>
                Entry: {s.entry?.toFixed(5)} | SL: {s.stop_loss?.toFixed(5)} | TP: {s.take_profit?.toFixed(5)}
              </div>
            </div>
          ))}
        </div>

        {/* 6. AI DECISION ENGINE */}
        <div style={{background:'#1e293b',borderRadius:'8px',padding:'16px',border:'1px solid #334155'}}>
          <h2 style={{color:'#38bdf8',fontSize:'16px',marginBottom:'12px'}}>AI DECISION ENGINE</h2>
          {signals.length > 0 && signals[0].institutional_bias && (
            <div style={{fontSize:'13px'}}>
              {[
                ['HTF Trend Alignment', signals[0].institutional_bias !== 'NEUTRAL'],
                ['Regime Confirmed', signals[0].institutional_bias === 'BREAKOUT'],
                ['Liquidity Event', signals[0].liquidity_state?.includes('SWEEP')],
                ['Dealer Pressure', signals[0].dealer_pressure !== 'NEUTRAL'],
                ['Confidence >= 75%', signals[0].confidence >= 0.75],
              ].map(([label, ok], i) => (
                <div key={i} style={{padding:'6px 0',borderBottom:'1px solid #1e293b',display:'flex',justifyContent:'space-between'}}>
                  <span>{label}</span>
                  <span style={{color:ok?'#22c55e':'#ef4444'}}>{ok?'? PASS':'? FAIL'}</span>
                </div>
              ))}
              <div style={{marginTop:'12px',padding:'8px',background:'#0f172a',borderRadius:'4px',textAlign:'center'}}>
                <span style={{fontWeight:'bold',color:'#38bdf8'}}>Decision: {signals[0]?.signal} {signals[0]?.pair}</span>
              </div>
            </div>
          )}
          {signals.length === 0 && <p style={{color:'#64748b'}}>Waiting for valid setup...</p>}
        </div>

        {/* 7. RISK PANEL */}
        <div style={{background:'#1e293b',borderRadius:'8px',padding:'16px',border:'1px solid #334155'}}>
          <h2 style={{color:'#38bdf8',fontSize:'16px',marginBottom:'12px'}}>RISK MANAGEMENT</h2>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'8px',fontSize:'13px'}}>
            <div>Risk/trade: <b>0.05%</b></div>
            <div>Max daily loss: <b>0.5%</b></div>
            <div>Max trades/day: <b>2</b></div>
            <div>Exposure: <b>0%</b></div>
            <div>Session: <b style={{color:'#22c55e'}}>London 07-11 UTC</b></div>
            <div>News Filter: <b style={{color:'#22c55e'}}>ON</b></div>
            <div>Regime Filter: <b style={{color:'#22c55e'}}>BREAKOUT+DISTRIBUTING</b></div>
            <div>Confidence Min: <b>75%</b></div>
          </div>
        </div>

        {/* ARCHIVE */}
        <div style={{background:'#1e293b',borderRadius:'8px',padding:'16px',border:'1px solid #334155',opacity:0.7}}>
          <h2 style={{color:'#64748b',fontSize:'16px',marginBottom:'12px'}}>HISTORICAL ARCHIVE</h2>
          <p style={{fontSize:'14px'}}>PRE_V3</p>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'4px',fontSize:'12px',color:'#94a3b8'}}>
            <div>Trades: <b>{arch.trades||0}</b></div>
            <div>Win Rate: <b>26.7%</b></div>
            <div>PF: <b>0.63</b></div>
            <div>P&L: <b style={{color:'#ef4444'}}>${arch.pnl||0}</b></div>
          </div>
          <div style={{marginTop:'8px',padding:'4px 8px',background:'#334155',borderRadius:'4px',fontSize:'11px',textAlign:'center',color:'#64748b'}}>STATUS: FROZEN</div>
        </div>

      </div>
    </div>
  );
}

export default App;
