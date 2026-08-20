"""AI models check"""
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity
from pathlib import Path

@registry.register
def check_ai_models() -> CheckResult:
    models_dir = Path('ai-service/models')
    if not models_dir.exists():
        return CheckResult("ai", "models", False, Severity.CRITICAL, "Models folder missing")
    models = list(models_dir.glob('*.joblib')) + list(models_dir.glob('*.zip'))
    passed = len(models) >= 6
    return CheckResult("ai", "models", passed, Severity.CRITICAL, f"{len(models)} models")
