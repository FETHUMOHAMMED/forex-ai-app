with open("backend/server.js","r",encoding="utf-8") as f:
    content = f.read()

old = "app.get('/api/stats'"
new = """// V3 Dashboard endpoint
app.get('/api/v3', (req, res) => {
  const db = new sqlite3.Database(dbPath);
  db.all("SELECT COUNT(*) as trades, SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) as wins, SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END) as losses, ROUND(SUM(pnl),2) as pnl FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL", (err, rows) => {
    if (err || !rows.length) return res.json({trades:0,wins:0,losses:0,pnl:0,archive_trades:156,archive_pnl:-2227.27});
    const r = rows[0];
    db.all("SELECT institutional_bias as regime, COUNT(*) as trades FROM trades WHERE strategy_version='V3_REGIME' AND pnl IS NOT NULL GROUP BY institutional_bias", (err2, regimes) => {
      db.close();
      res.json({
        trades: r.trades, wins: r.wins, losses: r.losses, pnl: r.pnl,
        archive_trades: 156, archive_pnl: -2227.27,
        regimes: regimes || []
      });
    });
  });
});

app.get('/api/stats'"""

content = content.replace(old, new)
with open("backend/server.js","w",encoding="utf-8") as f:
    f.write(content)
print("V3 endpoint added")
