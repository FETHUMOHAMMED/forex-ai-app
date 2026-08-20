# STRATEGY DEVELOPMENT PIPELINE

## Stage 1: Historical Data
- 8 years of USDJPY H4 data
- 10,000 bars
- Validated data integrity

## Stage 2: Data Validation
- Point-in-time correctness
- No look-ahead bias
- Gap detection
- Outlier removal

## Stage 3: Feature Generation
- EMA (50, 200)
- ATR (14)
- Session hours
- FVG detection

## Stage 4: Strategy Hypotheses
- 15 hypotheses tested
- FVG, OB, MSS combinations
- Different R:R ratios
- Session variations

## Stage 5: Backtest
- 115 trades (long-only FVG)
- 47% win rate
- PF 1.994
- +0.527R expectancy

## Stage 6: Cost/Slippage
- Typical costs: 0.1% edge reduction
- Extreme costs: Edge survives
- ID 163 event: Absorbed

## Stage 7: Walk-Forward
- 4 windows tested
- 75% profitable
- Parameter stability confirmed

## Stage 8: Out-of-Sample
- 2024-2025 (unseen)
- PF 1.510
- +0.293R expectancy

## Stage 9: Monte Carlo
- 10,000 simulations
- 100% probability of profit
- Worst case DD: 23R

## Stage 10: Robustness
- 29 parameter combinations
- 100% profitable
- Healthy plateaus

## Stage 11: Calibration
- Brier score: 0.1807 (good)
- Well-ranked predictions
- Underconfident at high probabilities

## Stage 12: Paper Trading
- READY TO BEGIN
- 60 days minimum
- 20+ trades target

## Stage 13: Controlled Live
- AWAITING PAPER VALIDATION
- $2,000 minimum capital
- 0.5% risk per trade

## Stage 14: Qualified Trades
- PENDING
- Only trades following all rules
- Documented evidence

## Stage 15: Strategy Promotion
- CURRENT STATUS: CANDIDATE
- Next: PAPER_VALIDATED
- Target: PRODUCTION_APPROVED
