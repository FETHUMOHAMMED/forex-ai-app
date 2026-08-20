"""DATA REQUIREMENTS FOR STRATEGY VALIDATION."""
from dataclasses import dataclass
from typing import List

@dataclass
class DataRequirements:
    """Minimum data needed for valid strategy research."""
    
    # Timeframes needed
    timeframes: List[str] = None
    
    # Currency pairs to test
    pairs: List[str] = None
    
    # Minimum history
    min_history_days: int = 180
    
    # Data quality requirements
    max_missing_bars_pct: float = 0.1
    max_spread_error_pct: float = 5.0
    
    def __post_init__(self):
        self.timeframes = self.timeframes or ["H4", "M15", "M5"]
        self.pairs = self.pairs or [
            "EURUSD", "GBPUSD", "USDJPY", 
            "AUDUSD", "USDCAD", "NZDUSD"
        ]
    
    def get_requirements(self) -> dict:
        """Return complete data requirements."""
        return {
            "timeframes": self.timeframes,
            "pairs": self.pairs,
            "min_history_days": self.min_history_days,
            "estimated_bars_needed": {
                "H4": self.min_history_days * 6,
                "M15": self.min_history_days * 96,
                "M5": self.min_history_days * 288
            },
            "quality_thresholds": {
                "max_missing_bars_pct": self.max_missing_bars_pct,
                "max_spread_error_pct": self.max_spread_error_pct
            },
            "required_fields": [
                "timestamp", "open", "high", "low", "close", 
                "volume", "spread"
            ]
        }

if __name__ == "__main__":
    req = DataRequirements()
    print(json.dumps(req.get_requirements(), indent=2))
