"""
Centralized Config Loader - Single source of truth.
All modules import settings from here. No hardcoded values.
"""
import sys, os, yaml
from pathlib import Path
from typing import Dict, List, Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config.yaml'

def _load_config() -> Dict[str, Any]:
    """Load YAML config once, cache forever."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

# Singleton config
_config = None

def get_config() -> Dict[str, Any]:
    global _config
    if _config is None:
        _config = _load_config()
    return _config

# Convenience accessors
def get_filters() -> Dict:
    return get_config()['filters']

def get_trading() -> Dict:
    return get_config()['trading']

def get_risk() -> Dict:
    return get_config()['risk']

def get_allowed_pairs() -> List[str]:
    return get_config()['trading']['allowed_pairs']

def get_blocked_pairs() -> List[str]:
    return get_config()['trading']['blocked_pairs']

def get_min_confidence() -> float:
    return get_config()['filters']['confidence']['min_confidence']

def get_min_inst_score() -> int:
    return get_config()['filters']['institutional']['min_score']

if __name__ == '__main__':
    config = get_config()
    print(f"Strategy: {config['strategy']['name']} v{config['strategy']['version']}")
    print(f"Allowed pairs: {get_allowed_pairs()}")
    print(f"Min confidence: {get_min_confidence()}")
    print(f"Min inst score: {get_min_inst_score()}")
    print(f"Risk per trade: {get_risk()['per_trade']}%")
