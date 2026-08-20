"""
Phase 5: Account Manager - Each account gets isolated state.
No shared signals, no shared positions, no shared config.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone

@dataclass
class AccountState:
    """Isolated state for one trading account"""
    name: str
    account_id: int
    server: str
    pairs: List[str] = field(default_factory=list)
    sessions: List[str] = field(default_factory=list)
    min_confidence: float = 0.53
    risk_percent: float = 0.05
    max_daily_trades: int = 20
    
    # Runtime state (NOT shared between accounts)
    daily_trades: int = 0
    open_positions: List[Dict] = field(default_factory=list)
    last_trade_time: Optional[str] = None
    consecutive_losses: int = 0
    daily_pnl: float = 0.0
    is_paused: bool = False
    pause_until: Optional[str] = None
    
    @property
    def can_trade(self) -> bool:
        if self.is_paused:
            if self.pause_until and datetime.fromisoformat(self.pause_until) > datetime.now(timezone.utc):
                return False
            self.is_paused = False
        return self.daily_trades < self.max_daily_trades


class AccountManager:
    """
    Manages multiple isolated trading accounts.
    Each account has its own state, config, and limits.
    """
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'config.json')
        
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.accounts: Dict[str, AccountState] = {}
        self._load_accounts()
    
    def _load_accounts(self):
        """Load all enabled accounts from config"""
        for acc_cfg in self.config.get('accounts', []):
            if not acc_cfg.get('enabled', True):
                continue
            
            state = AccountState(
                name=acc_cfg['name'],
                account_id=acc_cfg['account'],
                server=acc_cfg['server'],
                pairs=acc_cfg.get('pairs', ['EURUSD', 'GBPUSD']),
                sessions=acc_cfg.get('sessions_enabled', ['LONDON']),
                min_confidence=acc_cfg.get('min_confidence', 0.53),
                risk_percent=acc_cfg.get('risk_percent', 0.05),
                max_daily_trades=acc_cfg.get('max_daily_trades', 20),
            )
            self.accounts[state.name] = state
    
    def get_account(self, name: str) -> Optional[AccountState]:
        return self.accounts.get(name)
    
    def get_active_accounts(self) -> List[AccountState]:
        return [a for a in self.accounts.values() if a.can_trade]
    
    def record_trade(self, name: str, pnl: float):
        """Update account state after a trade closes"""
        acc = self.accounts.get(name)
        if not acc:
            return
        acc.daily_trades += 1
        acc.daily_pnl += pnl
        acc.last_trade_time = datetime.now(timezone.utc).isoformat()
        
        if pnl < 0:
            acc.consecutive_losses += 1
            if acc.consecutive_losses >= 5:
                acc.is_paused = True
                acc.pause_until = datetime.now(timezone.utc).isoformat()
        else:
            acc.consecutive_losses = 0
    
    def reset_daily(self, name: str):
        """Reset daily counters"""
        acc = self.accounts.get(name)
        if acc:
            acc.daily_trades = 0
            acc.daily_pnl = 0.0
    
    def status(self) -> List[Dict]:
        """Get status of all accounts"""
        return [{
            'name': a.name,
            'pairs': a.pairs,
            'daily_trades': a.daily_trades,
            'daily_pnl': round(a.daily_pnl, 2),
            'consecutive_losses': a.consecutive_losses,
            'is_paused': a.is_paused,
            'can_trade': a.can_trade,
        } for a in self.accounts.values()]


if __name__ == '__main__':
    mgr = AccountManager()
    for s in mgr.status():
        status = 'TRADING' if s['can_trade'] else 'PAUSED'
        print(f"{s['name']}: {s['pairs']} | {s['daily_trades']} trades | PnL={s['daily_pnl']} | {status}")
