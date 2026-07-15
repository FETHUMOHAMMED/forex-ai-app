"""Basic tests for the 5-layer signal pipeline"""
import sys, os, json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-service'))

def test_ict_features():
    """Test ICT features exist"""
    from risk.features import FEATURE_COLUMNS
    ict_features = ['fvg_buy', 'fvg_sell', 'mss_buy', 'mss_sell', 'ob_buy', 'ob_sell']
    for f in ict_features:
        assert f in FEATURE_COLUMNS, f"Missing: {f}"
    print(f"✅ All {len(ict_features)} ICT features present")

def test_config_loads():
    """Test config.json exists and has Demo2"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'config.json')
    with open(config_path) as f:
        cfg = json.load(f)
    demo2 = [a for a in cfg['accounts'] if a['name'] == 'Demo2'][0]
    assert demo2['enabled'] == True, "Demo2 should be enabled"
    assert len(demo2['pairs']) == 3, f"Expected 3 pairs, got {len(demo2['pairs'])}"
    print(f"✅ Demo2 active with {demo2['pairs']}")

def test_env_security():
    """Test .env is in gitignore"""
    gitignore_path = os.path.join(os.path.dirname(__file__), '..', '.gitignore')
    with open(gitignore_path) as f:
        content = f.read()
    assert '.env' in content, ".env not in gitignore!"
    assert 'config.json' in content, "config.json not in gitignore!"
    print("✅ Secrets protected in gitignore")

if __name__ == '__main__':
    test_ict_features()
    test_config_loads()
    test_env_security()
    print("\n🎉 All 3 tests passed!")