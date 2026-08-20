"""CAMPAIGN DASHBOARD - Daily status check."""
import json
from pathlib import Path
from datetime import datetime

def show_campaign_status():
    campaign_dir = Path("evidence/qualification_campaign")
    if not campaign_dir.exists():
        print("No campaign started. Run v3_qualification_campaign.py first.")
        return
    
    # Find latest manifest
    manifests = list(campaign_dir.glob("manifest_*.json"))
    if not manifests:
        print("No campaign manifest found.")
        return
    
    latest = max(manifests, key=lambda p: p.stat().st_mtime)
    with open(latest) as f:
        manifest = json.load(f)
    
    print("=" * 60)
    print("  V3 QUALIFICATION CAMPAIGN STATUS")
    print("=" * 60)
    print(f"  Campaign ID: {manifest['campaign_id']}")
    print(f"  Start: {manifest['start_date']}")
    print(f"  Status: {manifest['status']}")
    print()
    print("  METRICS:")
    m = manifest["metrics"]
    print(f"    Signals generated: {m['signals_generated']}")
    print(f"    Control rejections: {m['control_rejections']}")
    print(f"    Risk rejections: {m['risk_rejections']}")
    print(f"    Execution attempts: {m['execution_attempts']}")
    print(f"    Qualified trades: {m['qualified_trades']}")
    print(f"    Exceptions: {m['exceptions']}")
    print()
    print(f"  PROGRESS: {m['qualified_trades']}/50 qualified trades")
    print(f"  PERCENTAGE: {(m['qualified_trades']/50)*100:.1f}%")
    print("=" * 60)

if __name__ == "__main__":
    show_campaign_status()
