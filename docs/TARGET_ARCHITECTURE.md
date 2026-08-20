# FOREX-AI-APP Target Architecture - Complete

## THE PIPELINE

RESEARCH ? STRATEGY ? PORTFOLIO ? RISK ? CONTROL ? OMS ? EMS ? BROKERS ? LEDGER ? GOVERNANCE

## CRITICAL PRINCIPLE: Strategy-Agnostic Platform

The platform works with ANY strategy:
- V3_REGIME (current - unproven)
- V4 (future)
- Another ML model
- Statistical arbitrage
- Momentum strategy

NO rewrite needed for risk, OMS, execution, reconciliation, or governance layers.

## CURRENT IMPLEMENTATION STATUS

| Layer | Module | Status |
|-------|--------|--------|
| RESEARCH | packages/research/ | ? |
| STRATEGY | packages/strategy/ | ? (swappable) |
| PORTFOLIO | packages/portfolio/ | ? |
| RISK | packages/risk/ | ? |
| CONTROL | packages/integrity/ | ? |
| OMS | packages/execution/oms.py | ? |
| EMS | packages/execution/adapter.py | ? |
| BROKERS | MT5 (now), FIX (stub) | ? |
| LEDGER | packages/persistence/ | ? |
| GOVERNANCE | packages/security/ | ? |

## STRATEGY AGNOSTIC PROOF

To swap V3 for V4:
1. Create new strategy in packages/strategy/
2. Register in research platform
3. Same OMS, EMS, Risk, Portfolio used
4. No infrastructure changes

## THE COMPLETE FLOW (All Connected)

Research Platform
    ? (validated strategy)
Strategy Engine (V3/V4/any)
    ? (signal)
Portfolio Engine (exposure check)
    ? (allocation approved)
Risk Management (35 controls)
    ? (risk approved)
Control Plane (system health)
    ? (READY)
OMS (12-state lifecycle)
    ? (order created)
EMS (adapter)
    ?
MT5/FIX/REST (execution)
    ? (fill)
Post-Trade (reconciliation)
    ? (verified)
Governance (audit)
