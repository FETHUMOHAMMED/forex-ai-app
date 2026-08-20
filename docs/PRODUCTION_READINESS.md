# FOREX-AI-APP Production Readiness Checklist

> Current Status: VALIDATION PHASE (not production)
> Target: Provably safe under failure before production

## GATE 1: Data Integrity (MUST PASS)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1.1 | Every closed trade has MT5 position ID | ? | `mt5_position_id` column, invariants enforce |
| 1.2 | DB entry price matches MT5 fill price | ? | `actual_entry` vs `planned_entry` columns |
| 1.3 | DB exit price matches MT5 deal price | ? | Reconciliation tools verify |
| 1.4 | DB PnL matches MT5 net PnL | ? | Position-level reconciliation |
| 1.5 | No phantom trades (DB without MT5) | ? | Invariant: MUST_HAVE_MT5_POSITION |
| 1.6 | No orphan positions (MT5 without DB) | ? | Health monitor detects |
| 1.7 | All timestamps UTC with timezone | ? | Trade logger uses timezone.utc |
| 1.8 | Exit time > entry time always | ? | Invariant: EXIT_AFTER_ENTRY |

## GATE 2: Risk Controls (MUST PASS)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 2.1 | Position size <= configured max risk | ? | Hard invariant in position_sizing.py |
| 2.2 | Daily trade limit enforced | ? | Order boundary gate check #1 |
| 2.3 | Daily drawdown limit enforced | ? | Order boundary gate check #2 |
| 2.4 | Portfolio risk cap enforced | ? | Order boundary gate check #7 |
| 2.5 | Lot size within broker limits | ? | Order boundary gate check #3 |
| 2.6 | Margin check before order | ? | Order boundary gate check #6 |
| 2.7 | No order without risk check | ? | Trade state machine enforces RISK_APPROVED |

## GATE 3: Account Safety (MUST PASS)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 3.1 | Each account isolated (no shared MT5) | ? | AccountManager + per-worker sessions |
| 3.2 | Account identity verified before trade | ? | account_id in invariants |
| 3.3 | Demo trades excluded from live stats | ? | Account filter in all reports |
| 3.4 | Wrong account detection | ? | AccountMismatchError (FATAL) |
| 3.5 | Credentials never hardcoded | ? | SecretsManager + environment variables |

## GATE 4: Failure Handling (MUST PASS)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 4.1 | MT5 disconnect detected | ? | Health monitor, heartbeat |
| 4.2 | Stale heartbeat alerts | ? | Health monitor (ERROR >300s) |
| 4.3 | Auto-restart on crash | ? | Watchdog service |
| 4.4 | Missing metadata rejects trade | ? | require_regime(), require_metadata() |
| 4.5 | Stale signal rejects trade | ? | require_not_stale() |
| 4.6 | Invalid state transitions blocked | ? | TradeStateMachine |
| 4.7 | Error categories determine action | ? | FATAL/TRADE_REJECT/ACCOUNT_PAUSE/etc |

## GATE 5: Monitoring (MUST PASS)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 5.1 | Heartbeat monitoring active | ? | health_monitor.py checks every 60s |
| 5.2 | Database consistency checks | ? | db_mt5_consistency check |
| 5.3 | PnL integrity verification | ? | pnl_integrity check |
| 5.4 | Risk violation detection | ? | risk_violations check |
| 5.5 | Telegram/Slack alerts | ? | alerter.py |
| 5.6 | Diagnostic dashboard | ? | tools/diagnostics.py |

## GATE 6: V3 Validation Progress

| # | Milestone | Current | Target |
|---|-----------|---------|--------|
| 6.1 | Execution Verified | 1 | 10 |
| 6.2 | Risk Verified | 1 | 25 |
| 6.3 | Initial Review | 1 | 50 |
| 6.4 | Statistical Significance | 1 | 100 |
| 6.5 | Production Confidence | 1 | 300 |

## SUMMARY

| Gate | Status | Required for Production |
|------|--------|------------------------|
| 1. Data Integrity | ? 8/8 | YES |
| 2. Risk Controls | ? 7/7 | YES |
| 3. Account Safety | ? 5/5 | YES |
| 4. Failure Handling | ? 7/7 | YES |
| 5. Monitoring | ? 6/6 | YES |
| 6. V3 Validation | ? 1/300 | 100 minimum |

**The software is ready. The strategy is not yet validated.**
**Do not move to production until GATE 6 reaches at least 100 trades.**
