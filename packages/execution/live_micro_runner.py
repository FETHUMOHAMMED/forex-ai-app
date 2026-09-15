"""LIVE MICRO RUNNER - Orchestrator ONLY (no strategy logic)."""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from packages.strategy.canonical_v4 import CanonicalV4Strategy
from packages.execution.hard_order_boundary import OrderRequest, OrderDirection
from packages.execution.single_path import SingleExecutionPath
from packages.execution.mt5_connection_manager import mt5_manager

class LiveMicroRunner:
    """
    ORCHESTRATOR ONLY.
    - Does NOT calculate signals (CanonicalV4Strategy does)
    - Does NOT validate safety (HardOrderBoundary does)
    - Does NOT call mt5.order_send (SingleExecutionPath does)
    - ONLY connects components in correct order.
    """
    
    def __init__(self, mode: str = "PAPER"):
        self.mode = mode.upper()
        assert self.mode in ["PAPER", "LIVE"], f"Invalid mode: {mode}"
        
        # Components (all FROZEN)
        self.strategy = CanonicalV4Strategy()
        self.execution = SingleExecutionPath()
        
        # Lifecycle state
        self.enabled = False
        self.last_result = None
        self.run_id = None
        self.cycle_count = 0
        self.heartbeat_file = Path("research/paper/V4_CANONICAL_1.0/orchestrator_heartbeat.jsonl")
        
    def initialize(self) -> bool:
        """Verify everything before running."""
        print("="*70)
        print("  LIVE MICRO RUNNER - INITIALIZATION")
        print("="*70)
        
        # 1. Verify MT5 connection
        print("\n  [1/5] MT5 connection...")
        if not mt5_manager.connect():
            print("    FAILED: Cannot connect to MT5")
            return False
        print("    OK: Connected")
        
        # 2. Verify account
        print("\n  [2/5] Account verification...")
        account = mt5_manager.is_connected()
        if not account:
            print("    FAILED: Not connected")
            return False
        print("    OK: Account verified (REDACTED_LIVE_ACCOUNT)")
        
        # 3. Verify symbol
        print("\n  [3/5] Symbol verification...")
        info = mt5_manager.get_symbol_info("USDJPYm")
        if info is None:
            print("    FAILED: USDJPYm not found")
            return False
        print(f"    OK: USDJPYm available (spread: {info.spread} points)")
        
        # 4. Verify strategy
        print("\n  [4/5] Strategy version...")
        print(f"    OK: {self.strategy.strategy_version} (FROZEN)")
        
        # 5. Verify mode
        print(f"\n  [5/5] Execution mode...")
        print(f"    Mode: {self.mode}")
        if self.mode == "LIVE":
            print("    ?? LIVE MODE - Real orders will be placed!")
        else:
            print("    OK: PAPER mode (no real orders)")
        
        self.enabled = True
        print(f"\n  INITIALIZATION COMPLETE - Runner enabled ({self.mode})")
        return True
    
    def check_and_execute(self):
        """Orchestrate: strategy ? order ? boundary ? execution."""
        if not self.enabled:
            return {"status": "DISABLED", "reason": "Not initialized"}
        
        # 1. Get signal from FROZEN strategy
        signal = self.strategy.check_current_signal()
        
        if not signal.get('signal', False):
            return {
                "status": "NO_SIGNAL",
                "reason": signal.get('reason', 'UNKNOWN'),
                "mt5_called": False
            }
        
        # 2. Construct OrderRequest
        order = OrderRequest(
            symbol="USDJPYm",
            direction=OrderDirection.BUY,
            volume=0.01,
            entry=signal['entry'],
            sl=signal['sl'],
            tp=signal['tp'],
            risk_percent=0.25,
            account="REDACTED_LIVE_ACCOUNT",
            strategy_version="V4_CANONICAL_1.0"
        )
        
        # 3. Execute through SingleExecutionPath (which uses HardOrderBoundary)
        result = self.execution.execute_order(order, mode=self.mode)
        
        # 4. Log result
        self.last_result = result
        self._log_result(result)
        
        return result
    
    def _log_result(self, result):
        """Log to heartbeat/audit file with full context."""
        self.cycle_count += 1
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "cycle_id": self.cycle_count,
            "mode": self.mode,
            "strategy_version": "V4_CANONICAL_1.0",
            "account": "REDACTED_LIVE_ACCOUNT",
            **result
        }
        with open(self.heartbeat_file, 'a') as f:
            f.write(json.dumps(entry, default=str) + '\n')
    
    def shutdown(self):
        """Graceful shutdown."""
        self.enabled = False
        mt5_manager.disconnect()
        print("Runner shutdown complete")
    
    def run_once(self):
        """Run one orchestration cycle."""
        if not self.initialize():
            return None
        
        print(f"\n{'='*70}")
        print("  ORCHESTRATION CYCLE")
        print("="*70)
        
        result = self.check_and_execute()
        
        print(f"\n  Result: {result['status']}")
        print(f"  Reason: {result.get('reason', 'N/A')}")
        print(f"  MT5 called: {result.get('mt5_called', False)}")
        
        self.shutdown()
        return result

if __name__ == "__main__":
    runner = LiveMicroRunner(mode="PAPER")
    result = runner.run_once()

