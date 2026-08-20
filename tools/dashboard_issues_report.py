"""Dashboard Issues Report - For Advisor"""
print("=" * 65)
print("  DASHBOARD CRITICAL ISSUES")
print("=" * 65)

issues = [
    ("CRITICAL", "Equity Curve: $0-$600,000 on $19 account",
     "Using old Demo2 balance. Must show Live_Micro equity ($19.06)"),
    ("CRITICAL", "Win Rate: 0W/2L",
     "These are unqualified/Demo2 trades. V3 has 0 qualified closed trades"),
    ("CRITICAL", "Entry: 1.15123 (stale cached signal)",
     "This exact price caused ID 163 execution failure. Must show MT5 market price"),
    ("CRITICAL", "P&L: -$17.13 mixed sources",
     "$17 loss from Demo2 (ID 162) contaminating Live_Micro display"),
    ("HIGH", "Best/Worst: -$0.13/-$17.00",
     "Both should be excluded: ID 163 is EXECUTION_EXCEPTION, ID 162 is Demo2"),
    ("HIGH", "Missing: Institutional metadata on signals",
     "Should show Regime, Dealer Pressure, Liquidity, HTF Bias per advisor design"),
    ("HIGH", "Missing: V3 Validation Progress tracker",
     "Should show 0/10 Execution Verified, milestones"),
    ("MEDIUM", "Missing: Risk Panel",
     "Should show 0.05% risk, Session ON, News ON, Current exposure"),
]

for severity, issue, detail in issues:
    print(f"\n  [{severity[0]}] {issue}")
    print(f"      {detail}")

print(f"\n{'='*65}")
print(f"  CORRECT DISPLAY SHOULD BE:")
print(f"  V3 Qualified Trades: 0")
print(f"  V3 Win Rate: N/A (<10 trades)")
print(f"  V3 P&L: $0.00")
print(f"  Equity: $19.06 (MT5 broker balance)")
print(f"  Signals: Current MT5 market prices, not stale cache")
print(f"  PRE_V3: Archived separately as FROZEN")
print(f"{'='*65}")
