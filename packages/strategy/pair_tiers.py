"""TIERED PAIR CLASSIFICATION - Trade only what works."""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
from pathlib import Path

class PairTier(Enum):
    TRADE = "TRADE"                    # Validated, can trade
    CONDITIONAL = "CONDITIONAL"        # Promising, needs more data
    RESEARCH = "RESEARCH"              # Testing, not ready
    NO_TRADE = "NO_TRADE"              # Rejected, do not trade

@dataclass
class PairStatus:
    symbol: str
    tier: PairTier
    reason: str
    metrics: Dict

class PairTierManager:
    """Manages which pairs are tradeable based on validation."""
    
    def __init__(self):
        self.pairs = {}
        self.load_pair_data()
        
    def load_pair_data(self):
        """Load validated pair performance data."""
        
        # Based on our 8-year validation results
        self.pairs = {
            "USDJPYm": PairStatus(
                symbol="USDJPYm",
                tier=PairTier.TRADE,
                reason="Statistically significant edge (p=0.0049), PF 1.852, +0.466R expectancy",
                metrics={
                    "trades": 106,
                    "win_rate": 0.453,
                    "profit_factor": 1.852,
                    "expectancy_r": 0.466,
                    "p_value": 0.0049,
                    "confidence": "99%"
                }
            ),
            "USDCADm": PairStatus(
                symbol="USDCADm",
                tier=PairTier.CONDITIONAL,
                reason="Positive but not significant (p=0.153), PF 1.431, +0.264R expectancy",
                metrics={
                    "trades": 82,
                    "win_rate": 0.378,
                    "profit_factor": 1.431,
                    "expectancy_r": 0.264,
                    "p_value": 0.153,
                    "confidence": "85%"
                }
            ),
            "EURUSDm": PairStatus(
                symbol="EURUSDm",
                tier=PairTier.NO_TRADE,
                reason="Negative expectancy (p=0.599), PF 0.880, -0.083R expectancy",
                metrics={
                    "trades": 86,
                    "win_rate": 0.302,
                    "profit_factor": 0.880,
                    "expectancy_r": -0.083,
                    "p_value": 0.599,
                    "confidence": "N/A"
                }
            ),
            "GBPUSDm": PairStatus(
                symbol="GBPUSDm",
                tier=PairTier.NO_TRADE,
                reason="Negative expectancy (p=0.470), PF 0.850, -0.098R expectancy",
                metrics={
                    "trades": 101,
                    "win_rate": 0.327,
                    "profit_factor": 0.850,
                    "expectancy_r": -0.098,
                    "p_value": 0.470,
                    "confidence": "N/A"
                }
            ),
            "AUDUSDm": PairStatus(
                symbol="AUDUSDm",
                tier=PairTier.NO_TRADE,
                reason="Negative expectancy (p=0.538), PF 0.844, -0.105R expectancy",
                metrics={
                    "trades": 67,
                    "win_rate": 0.299,
                    "profit_factor": 0.844,
                    "expectancy_r": -0.105,
                    "p_value": 0.538,
                    "confidence": "N/A"
                }
            ),
            "USDCHFm": PairStatus(
                symbol="USDCHFm",
                tier=PairTier.NO_TRADE,
                reason="Negative expectancy (p=0.406), PF 0.794, -0.137R expectancy",
                metrics={
                    "trades": 66,
                    "win_rate": 0.333,
                    "profit_factor": 0.794,
                    "expectancy_r": -0.137,
                    "p_value": 0.406,
                    "confidence": "N/A"
                }
            ),
        }
    
    def get_tradeable_pairs(self) -> List[str]:
        """Get pairs approved for trading."""
        return [
            symbol for symbol, status in self.pairs.items()
            if status.tier == PairTier.TRADE
        ]
    
    def get_conditional_pairs(self) -> List[str]:
        """Get pairs under conditional review."""
        return [
            symbol for symbol, status in self.pairs.items()
            if status.tier == PairTier.CONDITIONAL
        ]
    
    def get_research_pairs(self) -> List[str]:
        """Get pairs for research only."""
        return [
            symbol for symbol, status in self.pairs.items()
            if status.tier == PairTier.RESEARCH
        ]
    
    def get_no_trade_pairs(self) -> List[str]:
        """Get pairs that should NOT be traded."""
        return [
            symbol for symbol, status in self.pairs.items()
            if status.tier == PairTier.NO_TRADE
        ]
    
    def should_trade(self, symbol: str) -> bool:
        """Check if a pair is approved for trading."""
        if symbol not in self.pairs:
            return False
        
        return self.pairs[symbol].tier == PairTier.TRADE
    
    def should_research(self, symbol: str) -> bool:
        """Check if a pair is in research phase."""
        if symbol not in self.pairs:
            return False
        
        return self.pairs[symbol].tier in [PairTier.CONDITIONAL, PairTier.RESEARCH]
    
    def should_avoid(self, symbol: str) -> bool:
        """Check if a pair should be avoided."""
        if symbol not in self.pairs:
            return True
        
        return self.pairs[symbol].tier == PairTier.NO_TRADE
    
    def display_tier_summary(self):
        """Display complete tier summary."""
        print("="*70)
        print("  PAIR TIER CLASSIFICATION")
        print("="*70)
        
        # Tier 1: Trade
        trade_pairs = self.get_tradeable_pairs()
        print(f"\n  TIER 1 - TRADE (Validated):")
        for symbol in trade_pairs:
            status = self.pairs[symbol]
            print(f"    ?? {symbol}")
            print(f"       {status.reason}")
        
        # Tier 2: Conditional
        conditional_pairs = self.get_conditional_pairs()
        print(f"\n  TIER 2 - CONDITIONAL (Research more):")
        for symbol in conditional_pairs:
            status = self.pairs[symbol]
            print(f"    ?? {symbol}")
            print(f"       {status.reason}")
        
        # Research
        research_pairs = self.get_research_pairs()
        print(f"\n  TIER 3 - RESEARCH ONLY:")
        for symbol in research_pairs:
            status = self.pairs[symbol]
            print(f"    ?? {symbol}")
            print(f"       {status.reason}")
        
        # No Trade
        no_trade_pairs = self.get_no_trade_pairs()
        print(f"\n  TIER 4 - NO TRADE (Rejected):")
        for symbol in no_trade_pairs:
            status = self.pairs[symbol]
            print(f"    ?? {symbol}")
            print(f"       {status.reason}")
        
        print(f"\n{'='*70}")
        print("  TRADING DECISION MATRIX")
        print("="*70)
        
        all_symbols = ["USDJPYm", "USDCADm", "EURUSDm", "GBPUSDm", "AUDUSDm", "USDCHFm"]
        for symbol in all_symbols:
            if symbol in self.pairs:
                status = self.pairs[symbol]
                decision = {
                    PairTier.TRADE: "TRADE",
                    PairTier.CONDITIONAL: "RESEARCH / CONDITIONAL",
                    PairTier.RESEARCH: "RESEARCH ONLY",
                    PairTier.NO_TRADE: "NO TRADE"
                }[status.tier]
                print(f"  {symbol:10s} -> {decision}")
    
    def save_tier_configuration(self):
        """Save tier configuration."""
        config = {}
        for symbol, status in self.pairs.items():
            config[symbol] = {
                "tier": status.tier.value,
                "reason": status.reason,
                "metrics": status.metrics
            }
        
        filepath = Path("research/pair_tiers.json")
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\nTier configuration saved to {filepath}")

if __name__ == "__main__":
    manager = PairTierManager()
    manager.display_tier_summary()
    manager.save_tier_configuration()
