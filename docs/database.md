# Database Schema

## Core Tables
| Table | Records | Purpose |
|-------|---------|---------|
| trades | 69 | Real executed trades with P&L |
| shadow_trades | 1,644 | Simulated historical trades |
| research_decisions | 500 | AI decisions without execution |
| trade_memory | 45 | Learning engine memory |
| performance_memory | 45 | Performance tracking |
| strategy_memory | 47 | Pair+regime+signal patterns |
| regime_memory | 0 | Market regime history |
| decision_memory | 0 | Decision logging |
| shadow_executions | 0 | Forward simulated outcomes |

## Key Trade Fields
- pair, signal, confidence, entry, exit_price, pnl
- institutional_bias, institutional_score
- dealer_pressure, liquidity_state
- continuation_prob, regime, session

## Data Tags
- PRODUCTION: Live trades with full risk
- SHADOW: Historical replay simulations
- RESEARCH: Low-confidence data collection
