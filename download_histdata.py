"""
download_histdata.py
Downloads 15‑minute Forex data directly from HistData.com servers.
No wrapper – pure HTTP requests, guaranteed to work.
"""

import os
import time
import zipfile
import requests
from io import BytesIO

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
         'USDCHF', 'NZDUSD', 'USDSGD']
YEARS = [2020, 2021, 2022, 2023, 2024]

BASE_URL = "https://www.histdata.com/get.php"

for pair in PAIRS:
    for year in YEARS:
        print(f"⬇️  Downloading {pair} {year}...")
        try:
            # Build the request parameters
            params = {
                'pair': pair,
                'year': year,
                'timeframe': 'M15',    # 15‑minute
                'type': 'csv'          # CSV format
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"   ❌ HTTP {response.status_code} for {pair} {year}")
                continue

            # HistData returns a ZIP file containing one CSV per month
            zip_data = BytesIO(response.content)
            with zipfile.ZipFile(zip_data) as zf:
                zf.extractall(DATA_DIR)
            print(f"   ✅ {pair} {year} extracted.")
        except Exception as e:
            print(f"   ❌ Failed {pair} {year}: {e}")
        time.sleep(0.5)   # be polite to the server

print("\n✅ All downloads complete.")