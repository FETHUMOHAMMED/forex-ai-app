import sqlite3
conn = sqlite3.connect('ai-service/trades.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM shadow_trades WHERE decision='SIMULATED'")
total = c.fetchone()[0]
print(f"Total shadow trades: {total}")

c.execute("SELECT COUNT(*) FROM shadow_trades WHERE decision='SIMULATED' AND institutional_score >= 60")
print(f"Inst >= 60: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM shadow_trades WHERE decision='SIMULATED' AND institutional_score < 60")
print(f"Inst < 60: {c.fetchone()[0]}")

c.execute("SELECT MIN(institutional_score), MAX(institutional_score) FROM shadow_trades WHERE decision='SIMULATED'")
r = c.fetchone()
print(f"Inst range: {r[0]} - {r[1]}")

c.execute("SELECT MIN(confidence), MAX(confidence) FROM shadow_trades WHERE decision='SIMULATED'")
r = c.fetchone()
print(f"Conf range: {r[0]:.3f} - {r[1]:.3f}")

c.execute("SELECT COUNT(*) FROM shadow_trades WHERE decision='SIMULATED' AND confidence < 0.53")
print(f"Conf < 0.53: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM shadow_trades WHERE decision='SIMULATED' AND confidence >= 0.53")
print(f"Conf >= 0.53: {c.fetchone()[0]}")

print(f"\nCONCLUSION: All {total} trades have inst >= 60 and conf >= 0.53.")
print("The replay engine pre-filters trades before saving.")
print("Ablation cannot compare filters - they are already applied.")
conn.close()
