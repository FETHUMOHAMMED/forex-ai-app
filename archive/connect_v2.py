with open("ai-service/daemon_v2.py","r",encoding="utf-8") as f:
    content = f.read()

# Replace old pipeline import with V2
old = "from core.signal_pipeline import SignalPipeline"
new = "from core.signal_pipeline_v2 import SignalPipelineV2 as SignalPipeline"
content = content.replace(old, new)

# Also fix the __init__ if needed
old_init = "self.pipeline = SignalPipeline()"
new_init = "self.pipeline = SignalPipeline()  # V2 with independent detectors"
if old_init in content:
    content = content.replace(old_init, new_init)

with open("ai-service/daemon_v2.py","w",encoding="utf-8") as f:
    f.write(content)
print("Daemon V2 now uses Pipeline V2")
