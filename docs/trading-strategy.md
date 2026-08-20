# Trading Strategy

## Current Research Mode
- Pairs: EURUSD, GBPUSD, USDJPY, USDCAD, NZDUSD, AUDUSD, EURJPY, GBPJPY, EURGBP, AUDJPY
- Sessions: London + Asian + NY (24h)
- Risk: 0.05% per trade
- Max daily trades: 20

## Proven Filters (from Rule Impact Analysis)
| Filter | Effect |
|--------|--------|
| Institutional Score >=55 | +$1,307 saved |
| Confidence >=0.53 | +$1,172 saved |
| Combined (Inst+Conf) | 60% WR, 1.97 PF |

## Top Edges (from 2,200+ data points)
- USDJPY + BREAKOUT: 67.9% WR
- NZDUSD + RANGING: 63.6% WR
- USDJPY overall: 57.5% WR
- Confidence 0.60+: 56.3% WR

## Avoid
- USDCAD (31% WR in replay)
- NEUTRAL dealer pressure
- Counter-trend trades
- NO_EVENT liquidity
