"""Model Registry - track model versions and metadata"""
import json
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH = Path("packages/strategy/model_registry.json")

class ModelRegistry:
    def __init__(self):
        self.registry = self._load()
    
    def _load(self):
        if REGISTRY_PATH.exists():
            return json.loads(REGISTRY_PATH.read_text())
        return {"models": []}
    
    def register_model(self, model_id, pair, timeframe, feature_version,
                       training_period, algorithm, hyperparameters,
                       validation_score, status="candidate"):
        entry = {
            "model_id": model_id,
            "pair": pair,
            "timeframe": timeframe,
            "feature_version": feature_version,
            "training_period": training_period,
            "algorithm": algorithm,
            "hyperparameters": hyperparameters,
            "validation_score": validation_score,
            "status": status,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        self.registry["models"].append(entry)
        REGISTRY_PATH.write_text(json.dumps(self.registry, indent=2))
        return entry
    
    def get_active_models(self):
        return [m for m in self.registry["models"] if m["status"] == "active"]
    
    def get_by_id(self, model_id):
        for m in self.registry["models"]:
            if m["model_id"] == model_id:
                return m
        return None

registry = ModelRegistry()
