import MetaTrader5 as mt5
import pandas as pd

class MT5DataLoader:
    def __init__(self):
        if not mt5.initialize():
            raise RuntimeError("MT5 not running – please open MetaTrader 5 first")

    def get_data(self, pair, timeframe, start, end):
        symbol = self._find_symbol(pair)
        if not symbol:
            print(f"   ❌ Symbol not found for {pair}")
            return None

        utc_from = pd.to_datetime(start)
        utc_to = pd.to_datetime(end)
        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)
        if rates is None or len(rates) == 0:
            print(f"   ❌ No MT5 data for {pair}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        return df[['open', 'high', 'low', 'close', 'volume']]

    def _find_symbol(self, pair):
        candidates = [pair, f"{pair}m", f"{pair}.", f"{pair}pro"]
        for sym in candidates:
            if mt5.symbol_select(sym, True):
                return sym
        return None