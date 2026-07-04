import MetaTrader5 as mt5
import pandas as pd
import numpy as np                           # ← was missing
from datetime import datetime, timedelta
import os

PAIRS = ['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','USDSGD']
END = datetime.now()
START = END - timedelta(days=365)

os.makedirs('data', exist_ok=True)

if not mt5.initialize():
    print("❌ MT5 not running.")
    exit()

for pair in PAIRS:
    candidates = [pair, f"{pair}m", f"{pair}.", f"{pair}pro"]
    symbol = None
    for sym in candidates:
        if mt5.symbol_select(sym, True):
            symbol = sym
            break
    if not symbol:
        print(f"❌ Symbol not found for {pair}")
        continue

    print(f"⬇️  Downloading ticks for {symbol} (month‑by‑month) …")

    all_ticks = []
    chunk_start = START
    while chunk_start < END:
        chunk_end = min(chunk_start + timedelta(days=30), END)
        ticks = mt5.copy_ticks_range(symbol, chunk_start, chunk_end, mt5.COPY_TICKS_ALL)
        if ticks is not None and len(ticks) > 0:
            all_ticks.append(ticks)
            print(f"   {chunk_start.strftime('%Y-%m')} → {len(ticks)} ticks")
        chunk_start = chunk_end + timedelta(seconds=1)

    if all_ticks:
        combined = np.concatenate(all_ticks)
        df = pd.DataFrame(combined)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df = df[['bid', 'ask', 'volume']]
        filename = f"data/{pair}_ticks.csv"
        df.to_csv(filename)
        print(f"   ✅ Saved {len(df)} ticks to {filename}\n")
    else:
        print(f"   ⚠️ No tick data at all for {pair} — skipping\n")

mt5.shutdown()
print("✅ Done.")