import MetaTrader5 as mt5
from datetime import datetime, timezone

mt5.initialize()

positions = mt5.positions_get()
if not positions:
    print('No open positions')
    mt5.shutdown()
    exit()

print('Ticket      Symbol     Type   Volume   Open Price   Current      PnL        Age      SL           TP')
print('-' * 105)

total_pnl = 0
old_count = 0
no_sl_count = 0
non_uj_count = 0

for p in positions:
    symbol = p.symbol
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        continue
    
    if p.type == 0:
        current = tick.bid
        ptype = 'BUY'
    else:
        current = tick.ask
        ptype = 'SELL'
    
    pnl = p.profit
    total_pnl += pnl
    
    open_time = datetime.fromtimestamp(p.time, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    age_hours = (now - open_time).total_seconds() / 3600
    
    warnings = ''
    if p.sl == 0:
        warnings += ' NO_SL'
        no_sl_count += 1
    if age_hours > 24:
        warnings += ' OLD'
        old_count += 1
    if 'USDJPY' not in symbol.upper():
        warnings += ' NON_UJ'
        non_uj_count += 1
    
    sl_val = p.sl if p.sl else 0
    tp_val = p.tp if p.tp else 0
    
    print(f'{p.ticket:<12} {symbol:<10} {ptype:<6} {p.volume:<8.2f} {p.price_open:<12.5f} {current:<12.5f} {pnl:<10.2f} {age_hours:<7.1f}h {sl_val:<12.5f} {tp_val:<12.5f}{warnings}')

print('-' * 105)
print(f'Total PnL: {total_pnl:.2f}')
print(f'No SL: {no_sl_count}/{len(positions)}')
print(f'Old (>24h): {old_count}/{len(positions)}')
print(f'Non-USDJPY: {non_uj_count}/{len(positions)}')

# Recommendation
print()
if non_uj_count > 0:
    print('RECOMMENDATION: Close all non-USDJPY positions immediately.')
    print('System is configured for USDJPY-only trading.')
if no_sl_count > 0:
    print('RECOMMENDATION: All positions must have stop losses.')
if old_count > 0:
    print('RECOMMENDATION: Implement timeout exits for positions > 24h.')

mt5.shutdown()
