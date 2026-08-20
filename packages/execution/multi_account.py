"""Multi-Account Architecture - Per-account isolation + Global Risk Manager."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum

class AccountState(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    HALTED = "HALTED"
    DISCONNECTED = "DISCONNECTED"

@dataclass
class AccountInstance:
    """One isolated trading account."""
    account_id: int
    account_name: str
    risk_limits: dict = field(default_factory=dict)
    positions: List[dict] = field(default_factory=list)
    state: AccountState = AccountState.ACTIVE
    
    def get_exposure(self) -> float:
        """Calculate account-level exposure."""
        return sum(p.get("notional", 0) for p in self.positions)
    
    def get_daily_pnl(self) -> float:
        """Account-level daily PnL."""
        return sum(p.get("pnl", 0) for p in self.positions)

@dataclass
class GlobalRiskManager:
    """Portfolio-level risk across ALL accounts."""
    max_total_exposure: float = 100000
    max_correlated_exposure: float = 50000
    max_total_drawdown: float = 0.10
    accounts: Dict[str, AccountInstance] = field(default_factory=dict)
    
    def add_account(self, account: AccountInstance):
        self.accounts[account.account_name] = account
    
    def get_total_exposure(self) -> float:
        """Sum of all account exposures."""
        return sum(acc.get_exposure() for acc in self.accounts.values())
    
    def get_correlated_exposure(self, currency: str = "USD") -> float:
        """Exposure to one currency across all accounts."""
        # Simplified: assume all EURUSD/GBPUSD have USD exposure
        usd_exposure = 0
        for acc in self.accounts.values():
            for pos in acc.positions:
                if "USD" in pos.get("pair", ""):
                    usd_exposure += pos.get("notional", 0)
        return usd_exposure
    
    def check_global_limits(self) -> dict:
        """Check global portfolio limits across all accounts."""
        total_exposure = self.get_total_exposure()
        usd_exposure = self.get_correlated_exposure("USD")
        total_pnl = sum(acc.get_daily_pnl() for acc in self.accounts.values())
        
        violations = []
        if total_exposure > self.max_total_exposure:
            violations.append(f"Total exposure ${total_exposure:,.0f} exceeds ${self.max_total_exposure:,.0f}")
        if abs(usd_exposure) > self.max_correlated_exposure:
            violations.append(f"USD exposure ${usd_exposure:,.0f} exceeds ${self.max_correlated_exposure:,.0f}")
        
        return {
            "total_exposure": total_exposure,
            "usd_exposure": usd_exposure,
            "total_pnl": total_pnl,
            "violations": violations,
            "trading_allowed": len(violations) == 0,
        }
    
    def halt_account(self, account_name: str, reason: str):
        """Halt one account without affecting others."""
        if account_name in self.accounts:
            self.accounts[account_name].state = AccountState.HALTED
            print(f"[GLOBAL RISK] Account {account_name} HALTED: {reason}")
    
    def halt_all_accounts(self, reason: str):
        """Emergency: halt all accounts."""
        for name in self.accounts:
            self.accounts[name].state = AccountState.HALTED
        print(f"[GLOBAL RISK] ALL ACCOUNTS HALTED: {reason}")
    
    def print_global_report(self):
        """Complete global risk report."""
        check = self.check_global_limits()
        
        print("=" * 70)
        print("  GLOBAL RISK MANAGER - MULTI-ACCOUNT")
        print("=" * 70)
        print(f"\n  ACCOUNTS:")
        for name, acc in self.accounts.items():
            print(f"    {name}: {acc.state.value} (exposure: ${acc.get_exposure():,.0f})")
        
        print(f"\n  GLOBAL METRICS:")
        print(f"    Total exposure: ${check['total_exposure']:,.0f}")
        print(f"    USD exposure: ${check['usd_exposure']:,.0f}")
        print(f"    Total PnL: ${check['total_pnl']:,.2f}")
        
        if check['violations']:
            print(f"\n  VIOLATIONS:")
            for v in check['violations']:
                print(f"    [RISK] {v}")
            print(f"\n  TRADING: BLOCKED")
        else:
            print(f"\n  TRADING: ALLOWED")
        print("=" * 70)


if __name__ == "__main__":
    # Create isolated accounts
    live_micro = AccountInstance(REDACTED_LIVE_ACCOUNT, "Live_Micro")
    demo2 = AccountInstance(REDACTED_DEMO_ACCOUNT, "Demo2")
    
    # Add positions (simulated)
    live_micro.positions.append({"pair": "EURUSD", "notional": 1150, "pnl": -1.17})
    demo2.positions.append({"pair": "EURUSD", "notional": 115500, "pnl": -17.00})
    
    # Global risk manager
    grm = GlobalRiskManager()
    grm.add_account(live_micro)
    grm.add_account(demo2)
    
    grm.print_global_report()
    
    # Test global risk violation
    print("\n  ADDING CORRELATED POSITIONS:")
    live_micro.positions.append({"pair": "GBPUSD", "notional": 1300, "pnl": 0})
    demo2.positions.append({"pair": "GBPUSD", "notional": 131000, "pnl": 0})
    
    grm.print_global_report()
    
    # Test account-level halt
    print("\n  ACCOUNT HALT TEST:")
    grm.halt_account("Live_Micro", "Risk violation")
    grm.print_global_report()
