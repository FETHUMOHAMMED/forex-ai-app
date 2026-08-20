"""
ML Pipeline Diagnostic - Is the ML engine alive?
"""
import sys, os, pickle, pandas as pd, numpy as np
sys.path.insert(0, 'ai-service')

print("=" * 55)
print("  ML PIPELINE DIAGNOSTIC")
print("=" * 55)

# 1. Check model files exist
model_dir = "ai-service/models"
if os.path.exists(model_dir):
    models_found = [f for f in os.listdir(model_dir) if f.endswith('.pkl')]
    print(f"\n1. MODEL FILES: {len(models_found)} found")
    for m in models_found:
        print(f"   {m}")
else:
    print(f"\n1. MODEL FILES: Directory '{model_dir}' NOT FOUND")
    # Try alternative locations
    for alt in ['models', 'ai-service/ai-service/models', '../models']:
        if os.path.exists(alt):
            print(f"   Found at: {alt}")
            model_dir = alt
            break

# 2. Try loading models
print(f"\n2. MODEL LOADING:")
if model_dir and os.path.exists(model_dir):
    for m in sorted(os.listdir(model_dir)):
        if m.endswith('.pkl'):
            try:
                with open(os.path.join(model_dir, m), 'rb') as f:
                    model = pickle.load(f)
                print(f"   {m}: LOADED (type={type(model).__name__})")
            except Exception as e:
                print(f"   {m}: FAILED - {str(e)[:60]}")
else:
    print("   No model directory found")

# 3. Check real_ai_service.py for model loading code
print(f"\n3. MODEL LOADING CODE:")
try:
    from real_ai_service import RealAIService
    svc = RealAIService()
    if hasattr(svc, 'models'):
        print(f"   Models dict: {list(svc.models.keys())}")
    else:
        print("   No 'models' attribute found")
    if hasattr(svc, 'pairs'):
        print(f"   Pairs: {svc.pairs[:5]}")
except Exception as e:
    print(f"   Cannot import: {e}")
    # Try reading the file directly
    with open('ai-service/real_ai_service.py', 'r') as f:
        content = f.read()
    if 'self.models' in content:
        print("   self.models found in source")
    if '.pkl' in content or 'pickle' in content:
        print("   pickle/model loading found in source")
    if 'predict_proba' in content:
        print("   predict_proba found in source")

# 4. Check where ml_sig=None comes from
print(f"\n4. ML_SIG=None SOURCE:")
with open('ai-service/real_ai_service.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'ml_signal = None' in line or 'ml_sig = None' in line:
        context = lines[max(0,i-2):i+3]
        print(f"   Line {i+1}: {line.strip()}")
        for c in context:
            print(f"      {c.rstrip()}")

print("\n" + "=" * 55)
