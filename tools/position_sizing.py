"""POSITION SIZING - Based on Monte Carlo worst case."""
import json
from pathlib import Path

def calculate_position_size(account_balance, risk_pct, worst_case_dd_r=23.3):
    """Calculate safe position size based on worst case."""
    
    # Maximum acceptable drawdown
    max_acceptable_dd_pct = 20  # Don't lose more than 20% of account
    
    # Calculate risk per trade needed to survive worst case
    max_risk_pct = max_acceptable_dd_pct / worst_case_dd_r
    
    # Use the smaller of desired risk and max safe risk
    safe_risk_pct = min(risk_pct, max_risk_pct)
    
    # Calculate position size
    risk_amount = account_balance * (safe_risk_pct / 100)
    
    return {
        "account_balance": account_balance,
        "desired_risk_pct": risk_pct,
        "safe_risk_pct": safe_risk_pct,
        "risk_amount": risk_amount,
        "worst_case_dd_amount": account_balance * (safe_risk_pct / 100) * worst_case_dd_r,
        "worst_case_dd_pct": safe_risk_pct * worst_case_dd_r
    }

def show_position_sizing_table():
    """Show position sizing for different account sizes."""
    print("="*70)
    print("  POSITION SIZING GUIDE")
    print("  Based on 23R worst-case drawdown")
    print("="*70)
    
    print(f"\n  Account     Risk/Trade   Worst DD     Max Acceptable")
    print(f"  " + "-"*60)
    
    accounts = [2000, 5000, 10000, 25000, 50000]
    
    for account in accounts:
        sizing = calculate_position_size(account, risk_pct=0.5)
        
        print(f"  ${account:>8,}  ${sizing['risk_amount']:>8.2f}   ${sizing['worst_case_dd_amount']:>7.0f}    {sizing['worst_case_dd_pct']:.1f}%")
    
    print(f"\n  KEY INSIGHTS:")
    print(f"  1. 0.5% risk = safe for all account sizes")
    print(f"  2. Worst case DD is about 12% (survivable)")
    print(f"  3. Never risk more than 0.5% initially")
    print(f"  4. Scale up only after proving consistency")
    
    print(f"\n  RECOMMENDED APPROACH:")
    print(f"  Start: 0.5% risk per trade")
    print(f"  After 3 months: 0.75% if no major issues")
    print(f"  After 6 months: 1.0% only if consistent")
    print(f"  Never exceed: 1.0% risk per trade")

if __name__ == "__main__":
    show_position_sizing_table()
