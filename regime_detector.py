"""
regime_detector.py – Classifies the current market regime on H1 data.
Uses ADX + ATR percentile to decide: 'trending', 'ranging', 'volatile'.
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

def detect_regime(pair, lookback_bars=100):
    """
    Returns one of: 'trending', 'ranging', 'volatile'
    Requires MT5 to be running and the symbol to be visible in Market Watch.
    """
    # 1. Find the correct MT5 symbol
    symbol = None
    for suffix in ['', 'm', '.', 'pro']:
        if mt5.symbol_select(pair + suffix, True):
            symbol = pair + suffix
            break
    if not symbol:
        return None

    # 2. Fetch H1 bars
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, lookback_bars)
    if rates is None or len(rates) < lookback_bars:
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df = df[['open','high','low','close']]

    # 3. Compute True Range and ATR
    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]

    # 4. Compute Directional Movement and ADX
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0

    atr_smooth = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / atr_smooth)
    minus_di = 100 * (minus_dm.rolling(14).mean() / atr_smooth)
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    adx = dx.rolling(14).mean().iloc[-1]

    # 5. ATR percentile (as % of current price)
    current_price = close.iloc[-1]
    if current_price == 0:
        return None
    atr_percent = (atr / current_price) * 100

    # 6. Classify regime
    if adx > 25:
        return 'trending'
    elif atr_percent > 0.3:   # ATR > 0.3% of price → volatile
        return 'volatile'
    else:
        return 'ranging'