import sys; sys.path.insert(0, '.')
from core.regime_strategy import strategy
from shared.trade_signal import TradeSignal

sig = TradeSignal(pair='EURUSD', direction='SELL', confidence=0.62, entry=1.1, stop_loss=1.103, take_profit=1.094, institutional_score=68, institutional_bias='BREAKOUT', dealer_pressure='DISTRIBUTING', liquidity_state='SWEEP_SELL')
result = strategy.validate(sig)
print('EURUSD BREAKOUT+DISTRIBUTING: ' + ('PASS' if result else sig.rejection_reason))

sig2 = TradeSignal(pair='GBPUSD', direction='SELL', confidence=0.62, entry=1.3, stop_loss=1.303, take_profit=1.294, institutional_score=68, institutional_bias='BREAKOUT', dealer_pressure='DISTRIBUTING', liquidity_state='SWEEP_SELL')
result2 = strategy.validate(sig2)
print('GBPUSD BREAKOUT+DISTRIBUTING: ' + ('PASS' if result2 else sig2.rejection_reason))

sig3 = TradeSignal(pair='EURUSD', direction='SELL', confidence=0.62, entry=1.1, stop_loss=1.103, take_profit=1.094, institutional_score=68, institutional_bias='RANGE', dealer_pressure='DISTRIBUTING', liquidity_state='SWEEP_SELL')
result3 = strategy.validate(sig3)
print('EURUSD RANGE+DISTRIBUTING: ' + ('PASS' if result3 else sig3.rejection_reason))
