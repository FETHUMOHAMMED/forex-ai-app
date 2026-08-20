"""PAPER TRADER - Matches backtest EXACTLY (4 filters only)."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.strategy.canonical_v4 import CanonicalV4Strategy

import importlib.util
logger_path = Path(__file__).resolve().parent / "signal_logger.py"
spec = importlib.util.spec_from_file_location("canonical_signal_logger", logger_path)
logger_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logger_module)
CanonicalSignalLogger = logger_module.CanonicalSignalLogger

from datetime import datetime, timezone

class PaperTrader:
    """Paper trading with EXACT backtest filters (no extra regime gate)."""
    
    def __init__(self):
        self.strategy = CanonicalV4Strategy()
        self.logger = CanonicalSignalLogger()
        self.criteria = self.logger.get_criteria()
        
    def check_and_log_signal(self):
        """Check signal using ONLY canonical strategy (4 filters)."""
        signal = self.strategy.check_current_signal()
        self.logger.log_signal(signal)
        return signal
    
    def run_once(self):
        """Run one paper trading check."""
        print("="*60)
        print("  PAPER TRADING CHECK (CANONICAL)")
        print("="*60)
        print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Strategy: V4_CANONICAL_1.0 (FROZEN)")
        print(f"  Filters: 4 (FVG + EMA50>EMA200 + London + BUY)")
        print(f"  NO EXTRA REGIME FILTER")
        
        signal = self.check_and_log_signal()
        
        print(f"\n  Signal: {signal.get('signal', False)}")
        if not signal.get('signal', False):
            print(f"  Reason: {signal.get('reason', 'UNKNOWN')}")
        else:
            print(f"  Entry: {signal.get('entry')}")
            print(f"  SL: {signal.get('sl')}")
            print(f"  TP: {signal.get('tp')}")
            print(f"  Risk: {signal.get('risk_percent')}%")
        
        print(f"\n  Logged to: research/paper/V4_CANONICAL_1.0/signal_log.jsonl")
        
        return signal

if __name__ == "__main__":
    trader = PaperTrader()
    signal = trader.run_once()
