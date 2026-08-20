with open("ai-service/daemon_v2.py","r",encoding="utf-8") as f:
    content = f.read()

# Add ML import
old_import = "from core.signal_pipeline import SignalPipeline"
new_import = "from core.signal_pipeline import SignalPipeline\nfrom ml.inference import predictor as ml_predictor"
content = content.replace(old_import, new_import)

# Replace the placeholder ML block
old_ml_start = "        # ML prediction (simplified - placeholder for real ML)"
old_ml_end = "        ml_conf = min(0.65, ml_conf)"

idx_start = content.find(old_ml_start)
idx_end = content.find(old_ml_end)

if idx_start > 0 and idx_end > idx_start:
    new_ml = """        # ML prediction from trained XGBoost models
        ml_signal, ml_conf = ml_predictor.predict(pair, df)
        if ml_signal is None:
            ml_signal = 'SELL' if df['close'].iloc[-1] < df['close'].iloc[-20] else 'BUY'
            ml_conf = 0.50"""
    
    content = content[:idx_start] + new_ml + content[idx_end+len(old_ml_end):]
    print("ML connected to daemon V2")
else:
    print(f"Could not find ML block. start={idx_start}, end={idx_end}")

with open("ai-service/daemon_v2.py","w",encoding="utf-8") as f:
    f.write(content)
