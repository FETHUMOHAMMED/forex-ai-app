import yfinance as yf
df = yf.download('EURUSD=X', period='5d', interval='15m')
print(f"Rows: {len(df)}")
print(df.tail())