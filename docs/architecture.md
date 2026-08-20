# FOREX-AI-APP Architecture

## System Overview
Multi-module institutional AI trading system with 9 volumes + adaptive filtering.

## Volumes
| Volume | Module | Purpose |
|--------|--------|---------|
| 1 | Market Microstructure | Dealer pressure, volume delta, bias |
| 2 | Liquidity Intelligence | Sweep detection, liquidity zones |
| 3 | Institutional Structure | Market phase, trend structure |
| 4 | Risk Allocation | Position sizing, exposure control |
| 5 | Decision Engine | Trade grading (A-F), gatekeeper |
| 6 | Learning Engine | Trade memory, pattern learning |
| 7 | Performance Intelligence | P&L tracking, feature analysis |
| 8 | Market Regime Intelligence | RANGING/BREAKOUT/TRENDING detection |
| 9 | Adaptive Strategy Optimization | Pair + regime + confidence calibration |
| 9.5 | Institutional Filters | Hard filters based on evidence |

## Data Pipeline
MT5 -> Daemon (ML+ICT+Inst) -> Signal Cache -> Watchdog -> Quality Gates -> Execution

## Active Filters (Research Mode)
- Institutional Score >= 55
- Confidence >= 0.53
- 10 liquid pairs
- Risk 0.05% per trade
