import sys
sys.path.insert(0, '.')
from packages.risk.order_boundary import enforce_order_boundary, RiskGateResult

# Test: Live_Micro $19 account, 0.01 lot EURUSD
gate = enforce_order_boundary(
    account_balance=19.06, account_equity=19.06, account_free_margin=19.06,
    trades_today=0, max_daily_trades=5, daily_pnl=0, max_daily_loss_pct=0.05,
    open_positions_count=0, max_open_positions=3, total_portfolio_risk_pct=0, max_portfolio_risk_pct=0.03,
    symbol="EURUSD", volume=0.01, entry_price=1.15542, stop_loss=1.15718,
    symbol_volume_min=0.01, symbol_volume_max=100, symbol_volume_step=0.01,
    symbol_tick_value=1.0, symbol_tick_size=0.00001, symbol_point=0.00001, symbol_contract_size=100000,
    max_risk_pct_per_trade=0.0005,
)

print(f"Result: {gate.result.value}")
print(f"Approved: {gate.is_approved}")
print(f"Actual Risk: ${gate.actual_risk_amount:.2f} ({gate.risk_pct_of_balance:.1f}% of balance)")
print(f"Reason: {gate.reason}")

# Test: Same but with 1.0 lot (should be rejected)
gate2 = enforce_order_boundary(
    account_balance=19.06, account_equity=19.06, account_free_margin=19.06,
    trades_today=0, max_daily_trades=5, daily_pnl=0, max_daily_loss_pct=0.05,
    open_positions_count=0, max_open_positions=3, total_portfolio_risk_pct=0, max_portfolio_risk_pct=0.03,
    symbol="EURUSD", volume=1.0, entry_price=1.15542, stop_loss=1.15718,
    symbol_volume_min=0.01, symbol_volume_max=100, symbol_volume_step=0.01,
    symbol_tick_value=1.0, symbol_tick_size=0.00001, symbol_point=0.00001, symbol_contract_size=100000,
    max_risk_pct_per_trade=0.0005,
)

print(f"\n1.0 Lot Test:")
print(f"Result: {gate2.result.value}")
print(f"Approved: {gate2.is_approved}")
print(f"Reason: {gate2.reason}")
