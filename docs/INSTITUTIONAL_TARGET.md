# Institutional Architecture - Current vs Target

## WHAT WE HAVE vs WHAT'S NEEDED

| Layer | Current | Target | Gap |
|-------|---------|--------|-----|
| Market Data | MT5 ticks | FX + News + Macro | Need news/macro feed |
| Data Platform | Feature contract | Clean/Normalize/Quality | Need data quality layer |
| Research Platform | Backtest=Paper=Live | + Walk-forward + Experiments | Need walk-forward |
| Real-Time Signal | Strategy Engine | Same | ? |
| Portfolio Engine | MISSING | Exposure/Correlation/Allocation | NEED |
| Risk Engine | Pre-trade + Budget | + Intraday + Portfolio + DD | Partial |
| OMS | Trade State Machine | + Idempotency + Order Mgmt | Partial |
| EMS | MT5 Direct | + Routing + Slippage + Liquidity | Partial |
| Brokers | MT5 | + FIX + ECN | Future |
| Post-Trade | Reconciliation | + P&L + Accounting | Partial |
| Risk & Control | Error Scanner | + Monitoring + Alerts + Audit | ? Have |

## PRIORITY ROADMAP

### Phase 1 (NOW): Complete Risk Engine
- [x] Pre-trade risk (budget, sizing)
- [ ] Intraday risk (drawdown tracking)
- [ ] Portfolio risk (correlation)
- [ ] Drawdown limits

### Phase 2: Portfolio Engine
- [ ] Exposure calculation
- [ ] Correlation matrix
- [ ] Capital allocation
- [ ] Diversification rules

### Phase 3: OMS Enhancement
- [x] State machine (11 states)
- [x] Idempotency
- [ ] Order lifecycle UI
- [ ] Manual override

### Phase 4: EMS
- [x] MT5 direct execution
- [ ] Smart order routing
- [ ] Slippage optimization
- [ ] Liquidity checks

### Phase 5: Brokers
- [x] MT5 (Exness)
- [ ] FIX protocol
- [ ] ECN integration
- [ ] Multi-broker routing

### Phase 6: Post-Trade
- [x] Reconciliation (25 checks)
- [ ] P&L attribution
- [ ] Cost analysis
- [ ] Accounting integration

## CURRENT GAP ANALYSIS

| Component | Have | Need | Effort |
|-----------|------|------|--------|
| Portfolio Engine | 0% | 100% | 2-4 weeks |
| Intraday Risk | 0% | 100% | 1-2 weeks |
| OMS UI | 0% | 100% | 2-3 weeks |
| Smart Routing | 0% | 100% | 4-8 weeks |
| FIX Protocol | 0% | 100% | 8-12 weeks |
| P&L Attribution | 0% | 100% | 2-3 weeks |

## BUT FIRST: STATISTICAL EVIDENCE

The advisor's #1 priority remains:
- 0 qualified trades now
- Need 300+ for production confidence
- No architecture work substitutes for this
