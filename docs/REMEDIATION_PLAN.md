# FOREX-AI-APP Remediation Plan
## From: Controlled Validation ? Production Trading

### Current Classification
**FOREX-AI-APP: controlled live-validation system (65/100 evidence-based)**
**NOT: production trading system**

---

## PHASE 0: IMMEDIATE (This Week) - Freeze & Fix

### 0.1 Production Freeze
- [x] Keep VALIDATION mode (0.05% risk, 5 trades/day)
- [x] Do NOT increase account size
- [x] Do NOT increase leverage
- [x] Do NOT remove any filters

### 0.2 Historical Data Cleanup
- [ ] Tag 153 contaminated records as LEGACY_INVALID
- [ ] Tag 112 timestamp-error records as LEGACY_INVALID
- [ ] Tag 1 phantom trade (ID 146) as LEGACY_INVALID
- [ ] Create clean V3-only view for validation counting

### 0.3 Execution Kill Switch
- [ ] Implement GLOBAL_TRADING_ENABLED flag
- [ ] Require ALL verifications before order:
  - account verified
  - risk verified
  - symbol verified
  - volume verified
  - SL verified
  - TP verified
  - spread verified
  - session verified
  - strategy verified

### 0.4 MT5 Reconciliation Fix
- [ ] Build deterministic Order?Position?Deal mapping
- [ ] Prove reconciliation for ID 163 (already done)
- [ ] Create automated reconciliation test

---

## PHASE 1: SHORT-TERM (1-2 Weeks) - Prove Integrity

### 1.1 Accumulate 10 Clean V3 Trades
Target: 10 MT5-verified closed trades with:
- [ ] 0 phantom trades
- [ ] 0 account contamination
- [ ] 0 impossible timestamps
- [ ] 0 sizing violations
- [ ] 0 identity mismatches
- [ ] 100% reconciliation match

### 1.2 Hard Sizing Boundary Proof
- [ ] Test: $19 account + 17.6 pip SL ? REJECTED correctly
- [ ] Test: $5,000 account + 17.6 pip SL ? APPROVED correctly
- [ ] Test: 1.0 lot on any account ? REJECTED
- [ ] Prove no code path can bypass sizing

### 1.3 Timestamp Integrity
- [ ] All new trades: entry_time < exit_time
- [ ] All timestamps: UTC with timezone
- [ ] DB constraint: CHECK(exit_time >= entry_time)

---

## PHASE 2: MEDIUM-TERM (1-3 Months) - Accumulate Evidence

### 2.1 25 Clean Trades
- [ ] Win rate analysis
- [ ] Profit factor
- [ ] Expectancy
- [ ] Average R
- [ ] Max consecutive losses
- [ ] Drawdown analysis

### 2.2 50 Clean Trades
- [ ] First serious strategy review
- [ ] Regime performance breakdown
- [ ] Pair performance breakdown
- [ ] Session performance breakdown

### 2.3 100 Clean Trades
- [ ] Out-of-sample validation
- [ ] Walk-forward validation
- [ ] Confidence calibration
- [ ] Monte Carlo analysis
- [ ] Compare vs PRE_V3 baseline
- [ ] Compare vs random baseline

---

## PHASE 3: LONG-TERM (3-6 Months) - Production Transition

### 3.1 Statistical Proof (300 trades)
- [ ] Positive expectancy after costs
- [ ] Profit factor > 1.3
- [ ] Acceptable maximum drawdown
- [ ] Regime-robust performance

### 3.2 Production Infrastructure
- [ ] PostgreSQL migration
- [ ] Prometheus/Grafana monitoring
- [ ] Docker deployment
- [ ] CI/CD pipeline
- [ ] Automated reconciliation
- [ ] Disaster recovery
- [ ] Model registry

### 3.3 Production Gates
- [ ] Gate 1: Execution Integrity (0 failures)
- [ ] Gate 2: Risk Integrity (0 violations)
- [ ] Gate 3: Strategy Validation (100+ trades)
- [ ] Gate 4: Statistical Significance (p < 0.05)
- [ ] Gate 5: Forward Paper Trading (matches live)
- [ ] Gate 6: Controlled Micro Live (current phase)

---

## CURRENT STATUS

Gate 1 (Execution): FAIL - 153 contaminated, 112 timestamp errors, 137 sizing violations
Gate 2 (Risk):      FAIL - Historical 18,526x sizing failure
Gate 3 (Strategy):  FAIL - 1 V3 trade (need 100+)
Gate 4 (Stats):     FAIL - No evidence
Gate 5 (Paper):     UNVERIFIED
Gate 6 (Micro Live): IN PROGRESS - 1 MT5-verified trade

**DO NOT ADVANCE TO PRODUCTION UNTIL ALL GATES PASS.**
