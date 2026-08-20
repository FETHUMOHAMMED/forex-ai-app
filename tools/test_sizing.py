import sys
sys.path.insert(0, '.')
from packages.risk.position_sizing import *

result = calculate_position_size(
    risk_params=RiskParams(
        account_balance=19.06,
        account_currency=AccountCurrency.USD,
        risk_pct=0.0005,
        max_daily_trades=5,
        max_portfolio_risk_pct=0.03,
    ),
    symbol_specs=EURUSD_SPECS,
    entry_price=1.15542,
    stop_loss_price=1.15718,
)
print(result.summary())
