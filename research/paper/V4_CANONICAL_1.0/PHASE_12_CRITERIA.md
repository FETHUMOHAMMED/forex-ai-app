# PHASE 11/12: PARALLEL VALIDATION (UPDATED)

## RESEARCH TRACK (Phase 11 - Paper)
Status: RUNNING (Day 3/90)
Purpose: Validate strategy edge statistically
Runner: continuous_runner.py (ONE instance)
Duration: 90 days OR 50+ qualified trades
Not compressible: Needs sufficient sample size

## EXECUTION TRACK (Phase 12 - Live Micro)
Status: READY for controlled test
Purpose: Validate EXECUTION, NOT profitability
Isolation: 8/8 PASS (verified)
Sample needed: 10-20 live trades
Not production: Still requires paper validation to pass

## THE TWO TRACKS ARE INDEPENDENT:
Paper PASS ? Strategy edge proven
Live Micro ? Execution quality proven
BOTH needed ? Production gate

## LIVE MICRO AUTHORIZATION CHECKLIST (ALL must be checked):
[ ] Correct MT5 account verified
[ ] USDJPYm only
[ ] BUY only
[ ] Maximum 1 position
[ ] Risk <= 0.25%
[ ] SL mandatory
[ ] TP mandatory
[ ] Kill switch tested
[ ] Reconciliation tested
[ ] Duplicate prevention tested
[ ] Restart recovery tested
[ ] Order boundary tested
[ ] Live monitoring running
[ ] Alerts running
[ ] Trade evidence logging running
[ ] Emergency close procedure tested
[ ] Operator explicitly authorizes live execution

## LIVE MICRO CONSTRAINTS:
- Tiny capital (NOT $11.69 - need $2,000+)
- Only tests execution behavior
- Does NOT prove profitability
- 10-20 trades for execution validation
- Cannot be used to "prove" strategy works

## WHAT 10-20 LIVE TRADES PROVE:
- Orders reach MT5 correctly
- SL/TP applied properly
- Reconciliation works
- No unauthorized trades
- No execution path violations

## WHAT 10-20 LIVE TRADES DO NOT PROVE:
- Strategy is profitable
- Strategy has positive expectancy
- Edge is statistically significant
- Production is ready
