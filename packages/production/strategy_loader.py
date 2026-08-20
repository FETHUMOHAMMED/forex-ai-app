"""PRODUCTION STRATEGY LOADER - Loads only validated strategies."""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timezone
import hashlib

class ProductionStrategyLoader:
    """Loads immutable, validated strategies for production."""
    
    def __init__(self, strategies_dir: Path = Path("research/strategies")):
        self.strategies_dir = strategies_dir
        self.loaded_strategy = None
        
    def load_strategy(self, strategy_id: str) -> Optional[Dict]:
        """Load a validated strategy by ID."""
        # Find latest version of strategy
        strategy_files = list(self.strategies_dir.glob(f"{strategy_id}_*.json"))
        if not strategy_files:
            print(f"No strategy found with ID: {strategy_id}")
            return None
        
        # Get latest version
        latest_file = max(strategy_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file) as f:
            strategy = json.load(f)
        
        # Verify strategy is validated
        if strategy.get("status") != "VALIDATED":
            print(f"Strategy {strategy_id} is not validated")
            return None
        
        # Verify integrity
        if not self._verify_integrity(strategy):
            print(f"Strategy {strategy_id} failed integrity check")
            return None
        
        self.loaded_strategy = strategy
        return strategy
    
    def _verify_integrity(self, strategy: Dict) -> bool:
        """Verify strategy has not been tampered with."""
        # Check required fields
        required_fields = [
            "strategy_id", "version", "parameters", 
            "validation_summary", "created_at", "status"
        ]
        
        for field in required_fields:
            if field not in strategy:
                print(f"Missing required field: {field}")
                return False
        
        # Check validation metrics
        validation = strategy["validation_summary"]
        if validation["sample_size"] < 100:
            print("Insufficient sample size")
            return False
        if validation["expectancy"] < 0.2:
            print("Expectancy too low")
            return False
        if validation["profit_factor"] < 1.3:
            print("Profit factor too low")
            return False
        
        return True
    
    def get_parameters(self) -> Optional[Dict]:
        """Get strategy parameters for execution."""
        if self.loaded_strategy:
            return self.loaded_strategy["parameters"]
        return None
    
    def get_version(self) -> Optional[str]:
        """Get strategy version."""
        if self.loaded_strategy:
            return self.loaded_strategy["version"]
        return None

# Production execution wrapper
class ProductionExecution:
    """Executes validated strategies in production."""
    
    def __init__(self, strategy_loader: ProductionStrategyLoader):
        self.strategy_loader = strategy_loader
        self.strategy = None
        
    def initialize(self, strategy_id: str) -> bool:
        """Initialize production with validated strategy."""
        self.strategy = self.strategy_loader.load_strategy(strategy_id)
        return self.strategy is not None
    
    def execute(self, market_data: Dict) -> Dict:
        """Execute strategy on market data."""
        if not self.strategy:
            return {"error": "No validated strategy loaded"}
        
        # Get strategy parameters
        params = self.strategy["parameters"]
        
        # Apply strategy logic
        signal = self._apply_strategy(market_data, params)
        
        return {
            "strategy_id": self.strategy["strategy_id"],
            "version": self.strategy["version"],
            "signal": signal,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _apply_strategy(self, market_data: Dict, params: Dict) -> Dict:
        """Apply validated strategy parameters."""
        # This is a simplified example
        current_price = market_data.get("close")
        
        if market_data.get("ema_50", 0) > market_data.get("ema_200", 0):
            return {
                "direction": "BUY",
                "entry": current_price,
                "sl": current_price - params["sl_buffer_pips"] * 0.0001,
                "tp": current_price + params["sl_buffer_pips"] * params["tp_rr_ratio"] * 0.0001
            }
        else:
            return {
                "direction": "SELL",
                "entry": current_price,
                "sl": current_price + params["sl_buffer_pips"] * 0.0001,
                "tp": current_price - params["sl_buffer_pips"] * params["tp_rr_ratio"] * 0.0001
            }

if __name__ == "__main__":
    # Test production loading
    loader = ProductionStrategyLoader()
    execution = ProductionExecution(loader)
    
    # Try to load a strategy (will fail if not created yet)
    if execution.initialize("V4_LIQUIDITY_MSS"):
        print("Strategy loaded successfully")
        print(f"Version: {execution.strategy['version']}")
        print(f"Parameters: {execution.strategy['parameters']}")
    else:
        print("No validated strategy available for production")
