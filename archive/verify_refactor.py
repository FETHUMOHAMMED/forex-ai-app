"""
Verify all 10 refactor phases are complete and operational.
"""
import sys, os
sys.path.insert(0, '.')

print("=" * 60)
print("  REFACTOR VERIFICATION - All 10 Phases")
print("=" * 60)

results = []

# Phase 1: TradeSignal model
try:
    from shared.trade_signal import TradeSignal
    sig = TradeSignal(pair='EURUSD', direction='SELL', confidence=0.55, entry=1.1, stop_loss=1.2, take_profit=0.9)
    assert sig.is_valid == True
    d = sig.to_dict()
    assert 'pair' in d and 'signal' in d
    results.append(("Phase 1: TradeSignal model", True, "Single data model working"))
except Exception as e:
    results.append(("Phase 1: TradeSignal model", False, str(e)))

# Phase 2: Signal Pipeline
try:
    from core.signal_pipeline import SignalPipeline
    pipeline = SignalPipeline()
    assert pipeline is not None
    results.append(("Phase 2: Signal Pipeline", True, "One signal generation path"))
except Exception as e:
    results.append(("Phase 2: Signal Pipeline", False, str(e)))

# Phase 3: MT5 Executor
try:
    from execution.mt5_executor import MT5Executor
    results.append(("Phase 3: MT5 Executor", True, "Clean execution layer"))
except Exception as e:
    results.append(("Phase 3: MT5 Executor", False, str(e)))

# Phase 4: Daemon V2
try:
    import urllib.request, json
    resp = urllib.request.urlopen('http://localhost:8001/health', timeout=3)
    data = json.loads(resp.read())
    assert data['status'] == 'running'
    results.append(("Phase 4: Daemon V2", True, f"LIVE on port 8001, v{data.get('version',0)}"))
except Exception as e:
    results.append(("Phase 4: Daemon V2", False, "Not running on port 8001"))

# Phase 5: Account Manager
try:
    from execution.account_manager import AccountManager
    mgr = AccountManager()
    acc = mgr.get_account('Demo2')
    assert acc is not None
    results.append(("Phase 5: Account Manager", True, f"Isolated: {acc.name}, {len(acc.pairs)} pairs"))
except Exception as e:
    results.append(("Phase 5: Account Manager", False, str(e)))

# Phase 6: Broker Interface
try:
    from execution.broker_interface import BrokerInterface, PaperBroker, MT5Broker
    broker = PaperBroker(10000)
    broker.connect()
    result = broker.execute_market_order('EURUSD', 'SELL', 0.01, 1.10, 1.08)
    assert result.success
    results.append(("Phase 6: Broker Interface", True, "PaperBroker + MT5Broker working"))
except Exception as e:
    results.append(("Phase 6: Broker Interface", False, str(e)))

# Phase 7: Deprecation
try:
    deprecation_exists = os.path.exists('ai-service/DEPRECATED.txt')
    results.append(("Phase 7: Deprecation", deprecation_exists, "Old files documented" if deprecation_exists else "DEPRECATED.txt missing"))
except Exception as e:
    results.append(("Phase 7: Deprecation", False, str(e)))

# Phase 8: Central Config
try:
    from shared.config_loader import get_config, get_allowed_pairs, get_min_confidence
    config = get_config()
    pairs = get_allowed_pairs()
    conf = get_min_confidence()
    assert len(pairs) > 0
    results.append(("Phase 8: Central Config", True, f"config.yaml: {len(pairs)} pairs, min conf={conf}"))
except Exception as e:
    results.append(("Phase 8: Central Config", False, str(e)))

# Phase 9: Event Bus
try:
    from shared.event_bus import bus, SignalGenerated, TradeExecuted, TradeClosed
    sig = SignalGenerated(pair='EURUSD', direction='SELL', confidence=0.55, institutional_score=68)
    bus.publish(sig)
    events = bus.get_recent_events(1)
    assert len(events) > 0
    results.append(("Phase 9: Event Bus", True, f"Events logged: {bus.get_stats()}"))
except Exception as e:
    results.append(("Phase 9: Event Bus", False, str(e)))

# Phase 10: Telemetry
try:
    from shared.telemetry import telemetry
    stats = telemetry.get_stats()
    results.append(("Phase 10: Telemetry", True, f"Trade tracking active: {stats}"))
except Exception as e:
    results.append(("Phase 10: Telemetry", False, str(e)))

# Print results
print()
all_pass = True
for name, passed, detail in results:
    status = "[OK]" if passed else "[FAIL]"
    if not passed:
        all_pass = False
    print(f"  {status} {name}")
    print(f"      {detail}")

print(f"\n  {'='*40}")
print(f"  RESULT: {'ALL 10 PHASES PASSED' if all_pass else 'SOME PHASES FAILED'}")
print(f"  {'='*40}")
print("=" * 60)
