# Phase 3 shadow compatibility boundary

Phase 3 adds adapters only. The adapters delegate to the verified legacy V3
objects and contain no signal, strategy, risk, sizing, broker, persistence, or
position-management rules.

## Scope

The boundary is exposed by `packages/compatibility/legacy_v3_shadow.py`:

- `ShadowSignalAdapter` delegates `RealAITrader` signal methods.
- `ShadowDecisionAdapter` delegates the existing `AutoTrader` decision/filter
  helpers, including the exact symbol-comparison behavior.
- `ShadowRiskAdapter` delegates the existing position-size calculation.
- `ShadowBrokerAdapter` delegates `MT5Broker.place_market_order`.
- `ShadowPersistenceAdapter` delegates entry and exit logging calls to an
  isolated recorder/logger.
- `ShadowExecutionAdapter` delegates the existing account loop.
- `ShadowPositionManagementAdapter` delegates trailing-stop and time-exit
  calls.

No adapter is imported by a production launcher or current production module.
There is no cache, database, runtime-config, or live-account composition.

## Safety boundary

Every dependency must explicitly expose `shadow_only = True`. Broker,
execution, and position-management adapters additionally verify that the
legacy object's module-level MT5 object is the exact supplied shadow gateway.
The test environment uses the Phase 2 fake MT5 module and isolated recorder
objects. A live MT5 object, HTTP client, account, or broker is rejected.

The wrappers do not write `signals_cache.json`, `runtime_config.json`,
`trades.db`, production logs, or ledgers. No real MT5 connection or order is
used by the tests.

## Equality rules

Parity comparisons are exact for decisions, risk/sizing results, broker
requests and results, persistence calls, errors, and delegated position
management. Signal output is exact except for the legacy `timestamp` field,
which is created at call time; the test removes only that named field before
comparison. This exception is explicit in
`tests/characterization/test_phase3_shadow_parity.py` and is not a general
normalization rule.

## Verification

- Phase 3 parity tests: 11/11 passed.
- Phase 2 characterization tests: 29/29 passed.
- Combined characterization discovery: 39/39 passed.
- Relevant existing regression tests: 47/47 passed.
- Phase 2 baseline JSON remained byte-identical at SHA-256
  `1A33D16E8CCF6E9532448F23631AA5E34FE5E12864C9CF5A961ACFB525E959BF`.
- `git diff --check` passed.

This is still a shadow/test boundary. It is not approved for production
rewiring or live execution.
