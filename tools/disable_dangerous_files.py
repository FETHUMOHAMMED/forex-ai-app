"""DISABLE ALL DANGEROUS EXECUTION FILES - Emergency containment."""
from pathlib import Path
import shutil

def disable_dangerous_files():
    """Rename dangerous files to .DISABLED so they can't execute."""
    
    # Files that can place REAL orders (not tests, not paper)
    dangerous_files = [
        "execution/broker_interface.py",
        "execution/mt5_executor.py",
        "institutional/position_manager.py",
        "tools/check_and_close.py",
        "tools/close_id164.py",
        "tools/close_unprotected.py",
        "tools/set_sltp_id164.py",
        "packages/execution/account_manager.py",
        "packages/execution/adapter.py",
        "packages/execution/mt5_identity.py",
        "packages/execution/pre_submission_gate.py",
        "packages/execution/software_sl.py",
        "packages/execution/trade_state_machine.py",
        "packages/risk/monetary_risk_gate.py",
        "packages/risk/order_boundary.py",
        "packages/risk/rms.py",
        "packages/integrity/execution/gate.py",
    ]
    
    disabled = []
    
    for filepath in dangerous_files:
        path = Path(filepath)
        if path.exists():
            disabled_path = Path(str(filepath) + ".DISABLED")
            path.rename(disabled_path)
            disabled.append(str(filepath))
            print(f"  ? Disabled: {filepath}")
        else:
            print(f"  - Not found: {filepath}")
    
    print(f"\n  Disabled {len(disabled)} dangerous files")
    return disabled

if __name__ == "__main__":
    disable_dangerous_files()
