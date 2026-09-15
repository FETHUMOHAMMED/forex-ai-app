# V4_CANONICAL_1.0 - FROZEN PAPER TRADING EXPERIMENT

## START DATE: 2026-08-23
## DURATION: 90 DAYS MINIMUM
## TARGET: 50+ QUALIFIED TRADES

## FROZEN STRATEGY (DO NOT CHANGE):
- Pair: USDJPYm (ONLY)
- Direction: BUY (ONLY)
- Session: London 07:00-11:00 UTC (ONLY)
- Setup: H4 Bullish FVG
- Bias: EMA50 > EMA200
- SL: 2.0x ATR
- TP: 4.0x ATR (2R)
- Risk: 0.25% (explicit)

## FORBIDDEN CHANGES:
? Don't add EURUSD
? Don't add SELL trades
? Don't change session hours
? Don't change R:R ratio
? Don't change risk percent
? Don't add more filters
? Don't remove filters
? Don't add AI/ML
? Don't modify FVG definition

## WHAT TO RECORD (EVERY evaluation):
- timestamp_utc
- symbol
- fvg_detected
- bullish_bias
- london_session
- decision (TRADE or REJECT)
- reason

## SUCCESS CRITERIA (after 90 days):
- 50+ qualified trades (or natural count)
- Expectancy > 0R
- PF > 1.15
- Zero safety violations
- Complete logs

## CURRENT STATUS:
- Day: 0 of 90
- Trades: 0
- Waiting for: Uptrend + FVG + London session
