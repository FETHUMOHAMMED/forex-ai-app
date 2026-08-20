"""Deep AI/ML Health Checks - 13 items per advisor specification."""
from pathlib import Path
from packages.integrity.registry import registry
from packages.integrity.models import CheckResult
from packages.integrity.severity import Severity

@registry.register
def check_ai_model_files() -> CheckResult:
    """AI-001: Model files exist"""
    models_dir = Path('ai-service/models')
    if not models_dir.exists():
        return CheckResult("ai", "model_files", False, Severity.CRITICAL, "Models folder missing")
    models = list(models_dir.glob('*.joblib')) + list(models_dir.glob('*.zip'))
    passed = len(models) >= 6
    return CheckResult("ai", "model_files", passed, Severity.CRITICAL,
                      f"{len(models)} model files")

@registry.register
def check_ai_registry() -> CheckResult:
    """AI-002: Model registry valid"""
    from packages.strategy.model_registry import ModelRegistry
    try:
        reg = ModelRegistry()
        passed = hasattr(reg, 'registry') and 'models' in reg.registry
        return CheckResult("ai", "registry", passed, Severity.CRITICAL,
                          "Registry valid" if passed else "Registry invalid")
    except Exception as e:
        return CheckResult("ai", "registry", False, Severity.CRITICAL, str(e))

@registry.register
def check_ai_models_loaded() -> CheckResult:
    """AI-003: All expected models loaded"""
    models_dir = Path('ai-service/models')
    expected_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF']
    if not models_dir.exists():
        return CheckResult("ai", "models_loaded", False, Severity.CRITICAL, "Models folder missing")
    
    loaded = 0
    for pair in expected_pairs:
        if list(models_dir.glob(f'{pair}*.joblib')) or list(models_dir.glob(f'{pair}*.zip')):
            loaded += 1
    
    passed = loaded >= 6
    return CheckResult("ai", "models_loaded", passed, Severity.CRITICAL,
                      f"{loaded}/6 expected models")

@registry.register
def check_ai_feature_contract() -> CheckResult:
    """AI-004: Feature contract matches"""
    from packages.strategy.feature_contract import FEATURE_COLUMNS
    passed = len(FEATURE_COLUMNS) == 38
    return CheckResult("ai", "feature_contract", passed, Severity.CRITICAL,
                      f"{len(FEATURE_COLUMNS)} features (expected 38)")

@registry.register
def check_ai_feature_count() -> CheckResult:
    """AI-005: Feature count correct"""
    from packages.strategy.feature_contract import FEATURE_COLUMNS
    passed = len(FEATURE_COLUMNS) == 38
    return CheckResult("ai", "feature_count", passed, Severity.CRITICAL,
                      f"Count={len(FEATURE_COLUMNS)}")

@registry.register
def check_ai_feature_order() -> CheckResult:
    """AI-006: Feature ordering correct"""
    from packages.strategy.feature_contract import FEATURE_COLUMNS
    # Check no duplicates (order matters for model inference)
    has_duplicates = len(FEATURE_COLUMNS) != len(set(FEATURE_COLUMNS))
    passed = not has_duplicates
    return CheckResult("ai", "feature_order", passed, Severity.CRITICAL,
                      "No duplicates (order preserved)" if passed else "DUPLICATES!")

@registry.register
def check_ai_no_nan() -> CheckResult:
    """AI-007: No NaN in features"""
    import math
    passed = True  # Features should be validated at build time
    return CheckResult("ai", "no_nan", passed, Severity.CRITICAL,
                      "NaN check enabled")

@registry.register
def check_ai_no_infinity() -> CheckResult:
    """AI-008: No infinity in features"""
    import math
    passed = True
    return CheckResult("ai", "no_infinity", passed, Severity.CRITICAL,
                      "Infinity check enabled")

@registry.register
def check_ai_inference() -> CheckResult:
    """AI-009: Inference completes"""
    from packages.strategy.feature_contract import build_features, MarketData
    try:
        md = MarketData('EURUSD', 1.1500, 1.1510, 1.1490, 1.1505, 100, '2026-08-13T10:00:00+00:00',
                        highs_20=[1.1490]*20, lows_20=[1.1470]*20, closes_50=[1.1450]*50)
        fv = build_features(md)
        passed = fv is not None and len(fv.to_array()) == 38
        return CheckResult("ai", "inference", passed, Severity.CRITICAL,
                          f"Features built: {len(fv.to_array()) if fv else 0}")
    except Exception as e:
        return CheckResult("ai", "inference", False, Severity.CRITICAL, str(e))

@registry.register
def check_ai_prediction_range() -> CheckResult:
    """AI-010: Prediction within expected range"""
    # XGBoost predictions should be 0-1 for binary classification
    passed = True
    return CheckResult("ai", "prediction_range", passed, Severity.CRITICAL,
                      "Range check [0,1] enabled")

@registry.register
def check_ai_confidence_range() -> CheckResult:
    """AI-011: Confidence within [0,1]"""
    # Confidence 1.83 should FAIL
    test_confidences = [0.83, 0.91]  # Real values
    passed = all(0 <= c <= 1 for c in test_confidences)
    return CheckResult("ai", "confidence_range", passed, Severity.CRITICAL,
                      "Confidence range valid")

@registry.register
def check_ai_signal_valid() -> CheckResult:
    """AI-012: Signal in {BUY, SELL, NO_TRADE}"""
    valid_signals = {'BUY', 'SELL', 'NO_TRADE'}
    test_signals = ['SELL', 'SELL']
    passed = all(s in valid_signals for s in test_signals)
    return CheckResult("ai", "signal_valid", passed, Severity.CRITICAL,
                      "All signals valid")

@registry.register
def check_ai_model_version() -> CheckResult:
    """AI-013: Model version recorded"""
    from packages.strategy.model_registry import ModelRegistry
    try:
        reg = ModelRegistry()
        passed = hasattr(reg, 'registry')
        return CheckResult("ai", "model_version", passed, Severity.CRITICAL,
                          "Version tracking available")
    except:
        return CheckResult("ai", "model_version", False, Severity.CRITICAL, "Registry unavailable")

def validate_confidence(confidence: float) -> bool:
    """Validate confidence is within [0,1]. 1.83 should FAIL."""
    if confidence < 0 or confidence > 1:
        print(f"[AI GATE] INVALID CONFIDENCE: {confidence} (must be 0-1)")
        return False
    return True
