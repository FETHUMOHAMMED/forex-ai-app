"""CANONICAL SIGNAL LOGGER - Single authoritative logging implementation."""
import json
from datetime import datetime, timezone
from pathlib import Path

class CanonicalSignalLogger:
    """THE ONLY signal logger for V4_CANONICAL_1.0 paper trading."""
    
    def __init__(self):
        self.base_dir = Path("research/paper/V4_CANONICAL_1.0")
        self.signal_log = self.base_dir / "signal_log.jsonl"
        self.trade_log = self.base_dir / "trade_log.jsonl"
        self.criteria_file = self.base_dir / "criteria.json"
        
        # Create directories if needed
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Load criteria
        with open(self.criteria_file, 'r') as f:
            self.criteria = json.load(f)
    
    def log_signal(self, signal_data: dict) -> dict:
        """Log a signal (trade or no-trade)."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy_version": "V4_CANONICAL_1.0",
            "criteria_version": self.criteria.get("frozen_date", "unknown"),
            **signal_data
        }
        
        with open(self.signal_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    def log_trade(self, trade_data: dict) -> dict:
        """Log an executed trade."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy_version": "V4_CANONICAL_1.0",
            "type": "TRADE",
            **trade_data
        }
        
        with open(self.trade_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    def get_criteria(self) -> dict:
        """Get frozen criteria."""
        return self.criteria

if __name__ == "__main__":
    logger = CanonicalSignalLogger()
    
    # Test logging
    result = logger.log_signal({
        "signal_decision": "NO_TRADE",
        "reason": "SYSTEM_TEST",
        "symbol": "USDJPYm"
    })
    
    print("="*60)
    print("  CANONICAL SIGNAL LOGGER TEST")
    print("="*60)
    print(f"  Logged: {result['signal_decision']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Strategy: {result['strategy_version']}")
    print(f"  Criteria: {result['criteria_version']}")
    print(f"  Log file: {logger.signal_log}")
