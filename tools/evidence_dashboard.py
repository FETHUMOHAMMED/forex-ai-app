"""EVIDENCE DASHBOARD - Shows validation status."""
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

def show_dashboard():
    evidence_dir = Path("evidence/live_validation")
    if not evidence_dir.exists():
        print("No validation evidence yet. Start the live validator first.")
        return
    
    all_records = []
    for file in evidence_dir.glob("*.jsonl"):
        with open(file) as f:
            for line in f:
                if line.strip():
                    all_records.append(json.loads(line))
    
    if not all_records:
        print("No records yet.")
        return
    
    rejection_reasons = Counter()
    decisions = Counter()
    
    for r in all_records:
        decisions[r["decision"]] += 1
        if r["decision"] == "REJECT":
            for gate, status in r["gates"].items():
                if status == "FAIL":
                    rejection_reasons[gate] += 1
    
    print("=" * 60)
    print("  LIVE VALIDATION DASHBOARD")
    print("=" * 60)
    print(f"  Total signals evaluated: {len(all_records)}")
    print(f"  Decisions:")
    for decision, count in decisions.most_common():
        print(f"    {decision}: {count}")
    print(f"\n  Rejection reasons:")
    for reason, count in rejection_reasons.most_common(10):
        print(f"    {reason}: {count}")
    print(f"\n  MT5 orders sent: {sum(1 for r in all_records if r['mt5_order_sent'])}")
    print(f"  Qualified trades: {sum(1 for r in all_records if r['qualified'])}")
    print("=" * 60)

if __name__ == "__main__":
    show_dashboard()
