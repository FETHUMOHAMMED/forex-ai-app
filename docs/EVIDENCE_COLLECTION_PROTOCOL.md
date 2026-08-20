# Evidence Collection Protocol

> V3_REGIME is now in EVIDENCE COLLECTION phase.
> The architecture is FROZEN. No modifications allowed.

## THE EXPERIMENT

**Question**: Does V3_REGIME have positive expectancy after costs?

**Method**: Natural signal generation ? execution pipeline ? qualification

**Rules**:
1. No manual trade intervention
2. No filter modification to force trades
3. No strategy optimization based on <50 trades
4. Every trade passes ALL 11 qualification checks
5. Blocked signals recorded but NOT counted

## QUALIFICATION CHECKS (ALL MUST PASS)

1. Fresh signal (< 120s old)
2. Entry deviation <= 5 pips
3. Valid SL (correct side of actual fill)
4. Valid TP (correct side of actual fill)
5. Spread within range
6. Volume <= 0.01 lots
7. Risk <= 0.05% of equity
8. MT5 position exists
9. Exact deal reconciliation matches
10. Timestamps valid (UTC)
11. Account identity matches

## TRACKING

| Metric | Target |
|--------|--------|
| Qualified closed trades | 10 ? 50 ? 100 ? 300 |
| Execution exceptions | 0 |
| Reconciliation failures | 0 |
| Risk violations | 0 |

## DO NOT

- Modify strategy based on first 10 trades
- Increase lot size before 100 qualified trades
- Add indicators before statistical validation
- Delete LEGACY_INVALID records
- Call the system profitable before 100+ trades with positive expectancy
