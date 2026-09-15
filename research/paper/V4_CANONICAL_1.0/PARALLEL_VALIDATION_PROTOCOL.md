# V4 PARALLEL VALIDATION PROTOCOL

## PRINCIPLE: Research and execution validation run in parallel WITHOUT contaminating each other.

## THREE TRACKS:

### TRACK A: HISTORICAL RESEARCH (Already Complete)
Status: ? DONE
- 8 years historical data replayed
- Walk-forward: 4/4 windows profitable
- Monte Carlo: 100% profitable
- Transaction costs: Survivable
- Robustness: 29/29 profitable
- OOS expectancy: +0.158R

### TRACK B: PROSPECTIVE PAPER (RUNNING)
Status: ? ACTIVE (Day 3/90)
Runner: continuous_runner.py (single instance)
Purpose: Point-in-time evidence, real-time pipeline testing
Not compressed: Must run full 90 days

### TRACK C: CONTROLLED LIVE MICRO (PENDING)
Status: ?? LOCKED - Requires execution isolation verification first
Purpose: Validate EXECUTION, not profitability
Constraints:
- Separate/isolated account
- USDJPYm only
- BUY only
- Max 1 position
- 0.25% risk max
- Mandatory SL/TP
- Kill switch active
- Reconciliation active
- Complete execution ledger
- No legacy executor
- No strategy modification
- No AI override

## FINAL VALIDATION GATE:
Track A (Historical) + Track B (Paper) + Track C (Execution) ? Production

## WHAT 14 DAYS CAN PROVE:
- Execution path works (Track C)
- Runner reliable (Track B)
- No safety violations
- Reconciliation passes

## WHAT 14 DAYS CANNOT PROVE:
- Strategy profitability (needs 50+ trades)
- Statistical significance
- Edge persists across regimes
