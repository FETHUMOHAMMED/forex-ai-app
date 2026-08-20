"""
Verify V2 Pipeline - ML + Independent Detectors + Live Signals
"""
import sys, os, urllib.request, json, time
sys.path.insert(0, '.')

print("=" * 60)
print("  V2 PIPELINE VERIFICATION")
print("=" * 60)

results = []

# 1. ML Models
print("\n1. ML MODELS")
import os as _os
model_dir = "ml/models"
if _os.path.exists(model_dir):
    models = [f for f in _os.listdir(model_dir) if f.endswith('.pkl')]
    results.append(("ML Models", len(models) == 6, f"{len(models)} models found"))
    for m in models:
        print(f"   {m}")
else:
    results.append(("ML Models", False, "No model directory"))

# 2. Independent Detectors
print("\n2. INDEPENDENT DETECTORS")
try:
    from institutional.dealer_detector import DealerDetector
    d = DealerDetector()
    results.append(("Dealer Detector", True, "V2 - directional pressure"))
    print("   DealerDetector: OK")
except Exception as e:
    results.append(("Dealer Detector", False, str(e)))

try:
    from institutional.liquidity_detector import LiquidityDetector
    l = LiquidityDetector()
    results.append(("Liquidity Detector", True, "V2 - sweep + imbalance"))
    print("   LiquidityDetector: OK")
except Exception as e:
    results.append(("Liquidity Detector", False, str(e)))

try:
    from institutional.structure_detector import StructureDetector
    s = StructureDetector()
    results.append(("Structure Detector", True, "V2 - trend/range/breakout"))
    print("   StructureDetector: OK")
except Exception as e:
    results.append(("Structure Detector", False, str(e)))

# 3. Pipeline V2
print("\n3. PIPELINE V2")
try:
    from core.signal_pipeline_v2 import SignalPipelineV2
    pipe = SignalPipelineV2()
    results.append(("Signal Pipeline V2", True, "Uses independent detectors"))
    print("   SignalPipelineV2: OK")
except Exception as e:
    results.append(("Signal Pipeline V2", False, str(e)))

# 4. Live Daemon
print("\n4. LIVE DAEMON")
try:
    resp = urllib.request.urlopen('http://localhost:8001/signals', timeout=5)
    data = json.loads(resp.read())
    sigs = data.get('signals', [])
    version = data.get('version', 0)
    results.append(("Daemon V2", version > 0, f"v{version}, {len(sigs)} signals"))
    for s in sigs:
        print(f"   {s['pair']} {s['signal']} conf={s['confidence']:.3f} inst={s.get('institutional_score',0):.0f}%")
except Exception as e:
    results.append(("Daemon V2", False, str(e)[:60]))

# 5. Institutional Variance Check
print("\n5. INSTITUTIONAL VARIANCE")
if sigs:
    scores = [s.get('institutional_score', 0) for s in sigs]
    has_variance = len(set(scores)) > 1
    no_neutral = all(s > 50 for s in scores)
    results.append(("Score Variance", has_variance, f"Scores: {scores}"))
    results.append(("No NEUTRAL default", no_neutral, f"All > 50" if no_neutral else "Some <= 50"))
    print(f"   Scores: {scores}")
    print(f"   Variance: {'YES' if has_variance else 'NO - still flat'}")
else:
    results.append(("Score Variance", False, "No signals to check"))

# Summary
print(f"\n{'='*60}")
all_pass = all(r[1] for r in results)
print(f"  RESULT: {'ALL CHECKS PASSED' if all_pass else 'SOME FAILED'}")
for name, passed, detail in results:
    status = "[OK]" if passed else "[FAIL]"
    print(f"  {status} {name}: {detail}")
print(f"{'='*60}")
