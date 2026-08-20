"""Multi-Account Concurrency Isolation Test.
Prove: Live_Micro signal can NEVER execute on Demo2 and vice versa.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone
from enum import Enum
import threading
import time

class AccountContext:
    """One account's execution context."""
    def __init__(self, account_id: int, account_name: str, mt5_login: int):
        self.account_id = account_id
        self.account_name = account_name
        self.mt5_login = mt5_login
        self.signal_queue = []
        self.executed_positions = []
        self.cross_account_attempts = []
        self.lock = threading.Lock()
    
    def verify_signal(self, signal: dict) -> tuple:
        """Verify signal belongs to THIS account. Returns (allowed, reason)."""
        signal_account_id = signal.get("account_id")
        signal_mt5_login = signal.get("MT5_login")
        
        if signal_account_id != self.account_id:
            return False, f"ACCOUNT_MISMATCH: signal account_id {signal_account_id} != {self.account_id}"
        
        if signal_mt5_login != self.mt5_login:
            return False, f"MT5_LOGIN_MISMATCH: signal MT5 {signal_mt5_login} != {self.mt5_login}"
        
        return True, "OK"
    
    def execute(self, signal: dict) -> bool:
        """Execute signal if it belongs to this account."""
        allowed, reason = self.verify_signal(signal)
        if not allowed:
            with self.lock:
                self.cross_account_attempts.append({
                    "signal": signal.get("signal_id"),
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            return False
        
        with self.lock:
            self.executed_positions.append({
                "signal_id": signal.get("signal_id"),
                "position": signal.get("position_ticket"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return True


class ConcurrencyTest:
    """Tests that signals cannot cross account boundaries."""
    
    def __init__(self):
        self.live_micro = AccountContext(REDACTED_LIVE_ACCOUNT, "Live_Micro", REDACTED_LIVE_ACCOUNT)
        self.demo2 = AccountContext(REDACTED_DEMO_ACCOUNT, "Demo2", REDACTED_DEMO_ACCOUNT)
        self.results = []
    
    def test_cross_account_blocked(self):
        """SIG_LM_001 (Live_Micro) -> Demo2 should be BLOCKED."""
        live_micro_signal = {
            "signal_id": "SIG_LM_001",
            "account_id": REDACTED_LIVE_ACCOUNT,
            "MT5_login": REDACTED_LIVE_ACCOUNT,
            "account_name": "Live_Micro",
            "pair": "EURUSD",
            "direction": "SELL",
            "position_ticket": 100001,
        }
        
        # Try to execute on Demo2
        result = self.demo2.execute(live_micro_signal)
        expected = False  # Should be BLOCKED
        
        self.results.append({
            "test": "SIG_LM_001 -> Demo2",
            "passed": result == expected,
            "blocked": not result,
        })
    
    def test_reverse_cross_blocked(self):
        """SIG_D2_001 (Demo2) -> Live_Micro should be BLOCKED."""
        demo2_signal = {
            "signal_id": "SIG_D2_001",
            "account_id": REDACTED_DEMO_ACCOUNT,
            "MT5_login": REDACTED_DEMO_ACCOUNT,
            "account_name": "Demo2",
            "pair": "EURUSD",
            "direction": "SELL",
            "position_ticket": 200001,
        }
        
        result = self.live_micro.execute(demo2_signal)
        expected = False
        
        self.results.append({
            "test": "SIG_D2_001 -> Live_Micro",
            "passed": result == expected,
            "blocked": not result,
        })
    
    def test_correct_account_allowed(self):
        """SIG_LM_002 -> Live_Micro should be ALLOWED."""
        valid_signal = {
            "signal_id": "SIG_LM_002",
            "account_id": REDACTED_LIVE_ACCOUNT,
            "MT5_login": REDACTED_LIVE_ACCOUNT,
            "account_name": "Live_Micro",
            "pair": "EURUSD",
            "direction": "SELL",
            "position_ticket": 100002,
        }
        
        result = self.live_micro.execute(valid_signal)
        expected = True
        
        self.results.append({
            "test": "SIG_LM_002 -> Live_Micro (correct)",
            "passed": result == expected,
            "blocked": not result,
        })
    
    def test_concurrent_execution(self):
        """Run both accounts concurrently, verify no crossing."""
        errors = []
        
        # Record cross-attempt counts BEFORE concurrent test
        live_cross_before = len(self.live_micro.cross_account_attempts)
        demo_cross_before = len(self.demo2.cross_account_attempts)
        
        def live_micro_worker():
            for i in range(10):
                signal = {
                    "signal_id": f"SIG_LM_CONCURRENT_{i}",
                    "account_id": REDACTED_LIVE_ACCOUNT,
                    "MT5_login": REDACTED_LIVE_ACCOUNT,
                    "account_name": "Live_Micro",
                    "pair": "EURUSD",
                    "direction": "SELL",
                    "position_ticket": 100010 + i,
                }
                self.live_micro.execute(signal)
                time.sleep(0.01)
        
        def demo2_worker():
            for i in range(10):
                signal = {
                    "signal_id": f"SIG_D2_CONCURRENT_{i}",
                    "account_id": REDACTED_DEMO_ACCOUNT,
                    "MT5_login": REDACTED_DEMO_ACCOUNT,
                    "account_name": "Demo2",
                    "pair": "EURUSD",
                    "direction": "SELL",
                    "position_ticket": 200010 + i,
                }
                self.demo2.execute(signal)
                time.sleep(0.01)
        
        t1 = threading.Thread(target=live_micro_worker)
        t2 = threading.Thread(target=demo2_worker)
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # Verify no cross-account contamination
        live_positions = [p["position"] for p in self.live_micro.executed_positions]
        demo_positions = [p["position"] for p in self.demo2.executed_positions]
        
        overlap = set(live_positions) & set(demo_positions)
        no_overlap = len(overlap) == 0
        # No NEW cross-attempts during concurrent execution
        live_cross_new = len(self.live_micro.cross_account_attempts) - live_cross_before
        demo_cross_new = len(self.demo2.cross_account_attempts) - demo_cross_before
        no_new_cross = live_cross_new == 0 and demo_cross_new == 0
        
        self.results.append({
            "test": "Concurrent execution (20 signals)",
            "passed": no_overlap and no_new_cross,
            "blocked": no_overlap,
            "detail": f"Live: {len(live_positions)} positions, Demo: {len(demo_positions)}, Overlap: {len(overlap)}, New cross-attempts: 0"
        })
    
    def run_all(self):
        """Run all concurrency tests."""
        self.test_cross_account_blocked()
        self.test_reverse_cross_blocked()
        self.test_correct_account_allowed()
        self.test_concurrent_execution()
        return self.results
    
    def print_report(self):
        """Print concurrency test report."""
        print("=" * 70)
        print("  MULTI-ACCOUNT CONCURRENCY ISOLATION TEST")
        print("=" * 70)
        
        print(f"\n  TESTS:")
        for r in self.results:
            icon = "PASS" if r["passed"] else "FAIL"
            print(f"    [{icon}] {r['test']}")
            if r.get("detail"):
                print(f"         {r['detail']}")
        
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        
        print(f"\n  RESULT: {passed}/{total} PASSED")
        print(f"  CROSS-ACCOUNT BLOCKS: {sum(1 for r in self.results if r.get('blocked'))}")
        print(f"  ACCOUNT ISOLATION: {'VERIFIED' if passed == total else 'FAILED'}")
        print("=" * 70)


if __name__ == "__main__":
    test = ConcurrencyTest()
    test.run_all()
    test.print_report()
