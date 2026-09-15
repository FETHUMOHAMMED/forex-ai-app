"""TWO-TIER AUTHORIZATION - Research vs Micro-Live Observation."""
import MetaTrader5 as mt5
from pathlib import Path

def check_two_tier_authorization():
    """Check both research and micro-live authorization."""
    print("="*70)
    print("  TWO-TIER AUTHORIZATION")
    print("="*70)
    
    if not mt5.initialize():
        print("  MT5 not available")
        return
    
    account = mt5.account_info()
    mt5.shutdown()
    
    if not account:
        print("  No account info")
        return
    
    balance = account.balance
    
    print(f"\n  Account: {account.login}")
    print(f"  Balance: ${balance:.2f}")
    
    # TIER 1: RESEARCH CAPITAL ($2,000)
    print(f"\n{'='*70}")
    print("  TIER 1: RESEARCH CAPITAL (Statistical Validation)")
    print("="*70)
    print(f"  Required: $2,000+")
    print(f"  Current: ${balance:.2f}")
    print(f"  Status: {'PASS ?' if balance >= 2000 else 'FAIL ?'}")
    print(f"  Purpose: Validate strategy edge with proper 0.25% risk")
    print(f"  Risk model: $5 per trade (matches commission normalization)")
    
    # TIER 2: MICRO-LIVE OBSERVATION ($100)
    print(f"\n{'='*70}")
    print("  TIER 2: MICRO-LIVE OBSERVATION (Execution Testing)")
    print("="*70)
    print(f"  Required: $100+")
    print(f"  Current: ${balance:.2f}")
    print(f"  Status: {'PASS ?' if balance >= 100 else 'FAIL ?'}")
    print(f"  Purpose: Observe real MT5 execution of V4 signals")
    print(f"  Risk model: Broker-minimum constrained (NOT 0.25%)")
    print(f"  Actual risk at 0.01 lots: ~3.75% at $100")
    print(f"  NOT VALID for statistical comparison")
    
    # RECOMMENDATION
    print(f"\n{'='*70}")
    print("  RECOMMENDATION")
    print("="*70)
    
    if balance >= 2000:
        print(f"  ? FULL AUTHORIZATION: Both tracks can run")
    elif balance >= 100:
        print(f"  ?? PARTIAL AUTHORIZATION: Micro-live observation ONLY")
        print(f"  ? Research capital insufficient for 0.25% risk model")
        print(f"  Recommendation: Deposit ${2000 - balance:.2f} more for full research")
    else:
        print(f"  ? NO AUTHORIZATION: Balance too low")
        print(f"  Need at least $100 for micro-live observation")
        print(f"  Need $2,000 for full research validation")
    
    print(f"\n{'='*70}")
    print("  IMPORTANT DISTINCTION")
    print("="*70)
    print(f"""
  RESEARCH TRACK: $2,000+ ? validates STRATEGY PROFITABILITY
  MICRO-LIVE: $100+ ? validates EXECUTION CORRECTNESS
  
  These are DIFFERENT experiments.
  Don't mix their results.
""")
    
    return balance

if __name__ == "__main__":
    check_two_tier_authorization()
