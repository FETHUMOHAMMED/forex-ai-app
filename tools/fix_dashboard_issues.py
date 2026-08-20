"""Document dashboard issues that MUST be fixed before showing to users"""
print("=" * 70)
print("  DASHBOARD ISSUES - REQUIRING IMMEDIATE FIX")
print("=" * 70)

issues = [
    ("CRITICAL", "Equity Curve shows $0-$600,000", 
     "Your Live_Micro balance is $19.06. This graph is using old demo data.",
     "Fix: Query V3_REGIME + Live_Micro only for equity data"),
    
    ("CRITICAL", "Win Rate 0.0% (0W/2L) on $0 P&L",
     "These are PRE_V3 or unqualified trades contaminating V3 display.",
     "Fix: Filter strategy_version='V3_REGIME' AND account='Live_Micro' AND execution_contract_valid=1"),
    
    ("CRITICAL", "Entry: 1.15123 for EURUSD signal",
     "This is the STALE cached signal price that caused ID 163 failure.",
     "Fix: Show current market price from MT5 tick, not cached signal entry"),
    
    ("CRITICAL", "Today: $0.00 but P&L shows -$17.13",
     "Mixed data sources - today is V3, total includes PRE_V3/Demo2.",
     "Fix: All numbers must come from same filtered query"),
    
    ("HIGH", "Total P&L: -$17.13",
     "This -$17 is from Demo2 trade (ID 162), not Live_Micro.",
     "Fix: Filter account='Live_Micro', exclude LEGACY_INVALID and EXECUTION_EXCEPTION"),
    
    ("HIGH", "Best/Worst Trade: -$0.13/-$17.00",
     "-$0.13 is ID 163 (EXECUTION_EXCEPTION, should not count)",
     "-$17.00 is ID 162 (Demo2, should not be in Live_Micro stats)",
     "Fix: Both trades should be excluded from performance display"),
    
    ("HIGH", "Risk:Reward: 1: (empty)",
     "No R:R shown - should calculate from SL/TP distances",
     "Fix: Calculate and display expected R multiple"),
    
    ("MEDIUM", "Missing institutional metadata on signals",
     "Should show: Regime, Dealer Pressure, Liquidity, HTF Bias",
     "Fix: Include institutional fields from signal cache"),
    
    ("MEDIUM", "Missing V3 Validation Progress",
     "Should show: 0/10 Execution Verified, 0/25 Risk Verified, etc.",
     "Fix: Add validation milestone tracker"),
    
    ("MEDIUM", "Missing Risk Panel",
     "Should show: Risk 0.05%, Session ON, News ON, Exposure",
     "Fix: Add risk management display"),
]

for severity, issue, detail, fix in issues:
    icon = {"CRITICAL": "X", "HIGH": "!", "MEDIUM": "-"}[severity]
    print(f"\n  [{icon}] [{severity}] {issue}")
    print(f"      Problem: {detail}")
    print(f"      Fix: {fix}")

print(f"\n{'='*70}")
print(f"  SUMMARY:")
print(f"  CRITICAL: 4 issues (Equity curve, Win Rate, Stale entry, Mixed P&L)")
print(f"  HIGH: 3 issues (Demo2 contamination, R:R missing, Execution exception)")
print(f"  MEDIUM: 3 issues (Institutional metadata, Validation, Risk panel)")
print(f"")
print(f"  CORRECT DASHBOARD DATA:")
print(f"  V3 Live_Micro qualified trades: 0")
print(f"  V3 Win Rate: N/A (insufficient data)")
print(f"  V3 P&L: $0.00")
print(f"  Equity Curve: $19.06 (actual broker balance)")
print(f"  Current signal entry: MT5 bid/ask (not 1.15123 stale cache)")
print(f"  PRE_V3 Archive: 156 trades, PF 0.63, -$2,227 (FROZEN)")
print(f"{'='*70}")
