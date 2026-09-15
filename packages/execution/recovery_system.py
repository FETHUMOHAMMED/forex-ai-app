"""RECOVERY SYSTEM - Handles crashes, restarts, and reconciliation."""
import MetaTrader5 as mt5
import json
from datetime import datetime, timezone
from pathlib import Path
import time

class RecoverySystem:
    """
    Handles recovery after crashes.
    Ensures idempotency - never duplicate orders.
    """
    
    def __init__(self):
        self.state_file = Path("research/recovery_state.json")
        self.mt5_connected = False
        self.last_reconciliation = None
        
    def check_system_health(self) -> Dict:
        """Check all system components."""
        health = {
            "mt5_connected": False,
            "python_running": True,
            "database_ok": False,
            "paper_runner": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Check MT5
        if mt5.initialize():
            health["mt5_connected"] = True
            mt5.shutdown()
        
        # Check state file
        if self.state_file.exists():
            health["database_ok"] = True
        
        # Check paper runner
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", 
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'continuous_runner' } | Measure-Object | Select-Object -ExpandProperty Count"],
            capture_output=True, text=True
        )
        runner_count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        health["paper_runner"] = runner_count > 0
        health["runner_count"] = runner_count
        
        return health
    
    def reconcile_after_restart(self) -> Dict:
        """
        CRITICAL: After any restart, reconcile with MT5.
        Discovers existing positions BEFORE doing anything.
        """
        print("="*70)
        print("  RECOVERY: POST-RESTART RECONCILIATION")
        print("="*70)
        
        if not mt5.initialize():
            return {"status": "ERROR", "reason": "MT5 not available"}
        
        # Get all positions (DO NOT submit new orders)
        positions = mt5.positions_get()
        orders = mt5.orders_get()
        
        mt5.shutdown()
        
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "open_positions": len(positions) if positions else 0,
            "pending_orders": len(orders) if orders else 0,
            "positions": [],
            "action": "RECONCILE_ONLY"
        }
        
        if positions:
            for pos in positions:
                result["positions"].append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == 0 else "SELL",
                    "volume": pos.volume,
                    "entry": pos.price_open,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "protected": pos.sl > 0 and pos.tp > 0
                })
        
        # DO NOT submit any new orders
        result["new_orders_submitted"] = 0
        result["message"] = "Reconciliation complete. No new orders sent."
        
        # Save state
        self.save_state(result)
        
        print(f"\n  Open positions: {result['open_positions']}")
        print(f"  Pending orders: {result['pending_orders']}")
        print(f"  New orders sent: {result['new_orders_submitted']}")
        print(f"\n  Action: RECONCILE ONLY (no new orders)")
        
        return result
    
    def handle_duplicate_runner(self) -> Dict:
        """Detect and handle duplicate runner instances."""
        health = self.check_system_health()
        runner_count = health.get("runner_count", 0)
        
        if runner_count > 1:
            return {
                "status": "WARNING",
                "issue": f"{runner_count} runner instances detected",
                "action": "KILL_ALL_AND_RESTART_ONE",
                "message": "Multiple runners detected. Must reduce to exactly 1."
            }
        elif runner_count == 1:
            return {
                "status": "OK",
                "runner_count": 1,
                "message": "Exactly one runner active"
            }
        else:
            return {
                "status": "OFFLINE",
                "runner_count": 0,
                "action": "START_RUNNER",
                "message": "No runner active. Should start paper runner."
            }
    
    def handle_broker_rejection(self, order_result: Dict) -> Dict:
        """Handle broker order rejection safely."""
        return {
            "status": "ORDER_REJECTED",
            "action": "DO_NOT_RETRY",
            "message": "Broker rejected order. Do NOT automatically retry.",
            "original_result": order_result
        }
    
    def handle_lost_response(self, pending_order: Dict) -> Dict:
        """
        Handle case where order may have succeeded but response lost.
        CRITICAL: Reconcile with MT5 BEFORE deciding to retry.
        """
        print("\n  WARNING: Order response lost. Reconciling with MT5...")
        
        if not mt5.initialize():
            return {"status": "ERROR", "message": "Cannot reconcile - MT5 unavailable"}
        
        # Check if position exists (order may have succeeded)
        positions = mt5.positions_get()
        mt5.shutdown()
        
        if positions and len(positions) > 0:
            return {
                "status": "ORDER_SUCCEEDED",
                "message": "Position found in MT5. Do NOT resubmit.",
                "position_exists": True
            }
        else:
            return {
                "status": "ORDER_DID_NOT_EXECUTE",
                "message": "No position found. May retry ONLY after manual review.",
                "position_exists": False
            }
    
    def save_state(self, state: Dict):
        """Save recovery state."""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def run_recovery_check(self):
        """Run complete recovery check."""
        print("="*70)
        print("  RECOVERY SYSTEM CHECK")
        print("="*70)
        
        # 1. System health
        health = self.check_system_health()
        print(f"\n  SYSTEM HEALTH:")
        print(f"    MT5: {'ONLINE' if health['mt5_connected'] else 'OFFLINE'}")
        print(f"    Python: {'RUNNING' if health['python_running'] else 'STOPPED'}")
        print(f"    Database: {'OK' if health['database_ok'] else 'MISSING'}")
        print(f"    Paper runner: {health.get('runner_count', 0)} instances")
        
        # 2. Duplicate check
        dup_check = self.handle_duplicate_runner()
        print(f"\n  DUPLICATE CHECK:")
        print(f"    Status: {dup_check['status']}")
        print(f"    Message: {dup_check['message']}")
        
        # 3. Reconcile
        print(f"\n  RECONCILIATION:")
        reconciliation = self.reconcile_after_restart()
        
        return {
            "health": health,
            "duplicate_check": dup_check,
            "reconciliation": reconciliation
        }

if __name__ == "__main__":
    recovery = RecoverySystem()
    results = recovery.run_recovery_check()
