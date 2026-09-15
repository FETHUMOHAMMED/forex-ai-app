"""STRATEGY REGISTRY - Explicit identity for every strategy."""
from enum import Enum
from typing import Dict, List
import json
from pathlib import Path
from datetime import datetime, timezone

class StrategyStatus(Enum):
    PRODUCTION = "PRODUCTION"  # Allowed to trade
    PAPER_ONLY = "PAPER_ONLY"  # Paper trading only
    READ_ONLY = "READ_ONLY"    # Can read data, cannot trade
    DISABLED = "DISABLED"      # Completely disabled
    ARCHIVED = "ARCHIVED"      # Moved to archive

class StrategyRegistry:
    """THE authoritative strategy registry."""
    
    def __init__(self):
        self.strategies = {}
        self.initialize_registry()
        
    def initialize_registry(self):
        """Initialize with all known strategies."""
        
        self.strategies = {
            # THE ONLY APPROVED STRATEGY
            "V4_CANONICAL_1.0": {
                "status": StrategyStatus.PAPER_ONLY.value,
                "pair": "USDJPYm",
                "direction": "BUY_ONLY",
                "session": "London (7-11 UTC)",
                "risk": "0.25%",
                "can_trade_live": False,  # Paper only for now
                "can_trade_paper": True,
                "files": [
                    "packages/strategy/canonical_v4.py",
                    "research/paper/V4_CANONICAL_1.0/continuous_runner.py"
                ]
            },
            
            # LEGACY STRATEGIES (must be disabled)
            "V3_REGIME": {
                "status": StrategyStatus.DISABLED.value,
                "pair": "MULTIPLE",
                "direction": "BOTH",
                "session": "VARIABLE",
                "risk": "UNKNOWN",
                "can_trade_live": False,
                "can_trade_paper": False,
                "files": [
                    "ai-service/auto_trader_exness.py.DISABLED",
                    "ai-service/real_ai_service.py"
                ]
            },
            
            "EURUSD_PPO": {
                "status": StrategyStatus.DISABLED.value,
                "pair": "EURUSDm",
                "direction": "BOTH",
                "session": "VARIABLE",
                "risk": "UNKNOWN",
                "can_trade_live": False,
                "can_trade_paper": False,
                "files": [
                    "ai-service/models/EURUSD_ppo_trader.zip.DISABLED"
                ]
            },
            
            "LEGACY_MANUAL": {
                "status": StrategyStatus.ARCHIVED.value,
                "pair": "MULTIPLE",
                "direction": "BOTH",
                "session": "VARIABLE",
                "risk": "UNKNOWN",
                "can_trade_live": False,
                "can_trade_paper": False,
                "files": [
                    "execution/broker_interface.py.DISABLED",
                    "execution/mt5_executor.py.DISABLED"
                ]
            }
        }
    
    def get_production_strategy(self) -> str:
        """Return the ONLY strategy allowed in production."""
        for name, config in self.strategies.items():
            if config["status"] == StrategyStatus.PRODUCTION.value:
                return name
        return "NONE_YET"  # V4 is paper-only currently
    
    def verify_no_legacy_trading(self) -> Dict:
        """Verify legacy strategies cannot trade."""
        issues = []
        
        for name, config in self.strategies.items():
            if name != "V4_CANONICAL_1.0":
                if config["can_trade_live"]:
                    issues.append(f"{name} can still trade live!")
                if config["status"] not in [StrategyStatus.DISABLED.value, StrategyStatus.ARCHIVED.value]:
                    issues.append(f"{name} is not disabled!")
        
        return {
            "clean": len(issues) == 0,
            "issues": issues,
            "production_strategy": self.get_production_strategy()
        }
    
    def display_registry(self):
        """Display complete registry."""
        print("="*70)
        print("  STRATEGY REGISTRY")
        print("="*70)
        
        for name, config in self.strategies.items():
            status_icon = {
                "PRODUCTION": "??",
                "PAPER_ONLY": "??",
                "READ_ONLY": "??",
                "DISABLED": "??",
                "ARCHIVED": "?"
            }.get(config["status"], "?")
            
            print(f"\n  {status_icon} {name}")
            print(f"    Status: {config['status']}")
            print(f"    Pair: {config['pair']}")
            print(f"    Direction: {config['direction']}")
            print(f"    Can trade live: {config['can_trade_live']}")
            print(f"    Can trade paper: {config['can_trade_paper']}")
        
        verification = self.verify_no_legacy_trading()
        
        print(f"\n{'='*70}")
        print("  VERIFICATION")
        print("="*70)
        print(f"  Production strategy: {verification['production_strategy']}")
        print(f"  No legacy trading: {'YES ?' if verification['clean'] else 'NO ?'}")
        
        if not verification["clean"]:
            for issue in verification["issues"]:
                print(f"    ?? {issue}")
    
    def save_registry(self):
        """Save registry to file."""
        filepath = Path("research/strategy_registry.json")
        
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategies": self.strategies,
            "production": self.get_production_strategy()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nRegistry saved to {filepath}")

if __name__ == "__main__":
    registry = StrategyRegistry()
    registry.display_registry()
    registry.save_registry()
