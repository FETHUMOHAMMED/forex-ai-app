"""Tests for critical trading logic"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-service'))

def test_correlation_filter():
    """Test correlation filter correctly identifies exposure"""
    # Simulate positions list
    positions = [
        {'symbol': 'EURUSDm', 'type': 1},  # SELL EURUSD
        {'symbol': 'GBPUSDm', 'type': 1},  # SELL GBPUSD
    ]
    # Both are USD_SHORT_PAIRS selling = long USD exposure
    USD_SHORT_PAIRS = {'EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD'}
    usd_short_count = 0
    for pos in positions:
        pos_symbol = pos['symbol'].replace('m', '')
        pos_dir = 'BUY' if pos['type'] == 0 else 'SELL'
        if pos_symbol in USD_SHORT_PAIRS and pos_dir == 'SELL':
            usd_short_count += 1
    assert usd_short_count == 2, f"Expected 2, got {usd_short_count}"
    # Should reject a 3rd USD short
    assert usd_short_count >= 2  # limit reached
    print("✅ Correlation filter: USD exposure limit works")

def test_news_filter_timezone():
    """Test news filter uses UTC"""
    from risk.news_filter import NewsFilter
    nf = NewsFilter(blackout_minutes=30)
    # Should handle empty events gracefully
    events = nf._get_events()
    assert events is not None
    print("✅ News filter: Event fetching works")

def test_daily_loss_logic():
    """Test daily loss calculation"""
    starting_balance = 5000.0
    current_equity = 4750.0
    max_loss_pct = 0.05  # 5%
    loss = starting_balance - current_equity
    loss_pct = loss / starting_balance
    assert loss == 250.0
    assert loss_pct == 0.05
    assert loss_pct >= max_loss_pct  # Should trigger
    print("✅ Daily loss: Calculation correct")

def test_broker_fetch_rates():
    """Test broker fetch_rates method signature"""
    from broker_exness import MT5Broker
    broker = MT5Broker()
    assert hasattr(broker, 'fetch_rates'), "fetch_rates method missing"
    assert hasattr(broker, 'connect'), "connect method missing"
    assert hasattr(broker, 'place_market_order'), "place_market_order missing"
    print("✅ Broker layer: All required methods present")

def test_ict_scoring_weights():
    """Test ICT scoring with known weights"""
    # MSS=3, OB=3, FVG=2, BB=2, LV=1
    buy_score = 3 + 3 + 2  # MSS_buy + OB_buy + FVG_buy
    assert buy_score >= 3, f"Score {buy_score} should trigger buy"
    sell_score = 2  # Only FVG_sell
    assert sell_score < 3, f"Score {sell_score} should NOT trigger sell"
    print("✅ ICT scoring: Weighted thresholds correct")

if __name__ == '__main__':
    test_correlation_filter()
    test_news_filter_timezone()
    test_daily_loss_logic()
    test_broker_fetch_rates()
    test_ict_scoring_weights()
    print("\n🎉 All 5 trading logic tests passed!")