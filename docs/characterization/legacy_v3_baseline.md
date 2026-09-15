# Legacy V3 Characterization Baseline

Status: Phase 2 characterization only. No production module was migrated,
rewired, disabled, deleted, or edited.

Reference path:

```text
ai-service/ai_service_daemon.py
  -> real_ai_service.py::RealAITrader
  -> localhost:8001/signals/{pair}
  -> ai-service/auto_trader_exness.py
  -> ai-service/broker_exness.py
  -> MetaTrader5
```

## Reproducible test commands

Signal and execution characterization (23 tests):

```text
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
ai-service\venv\Scripts\python.exe -m unittest discover -s tests/characterization -p 'test_*.py' -v
```

Initial result before the expanded gate cases: **23 passed**.

The machine-readable expected-output artifact is
`tests/characterization/legacy_v3_baseline.json`.

Existing relevant regression tests (47 tests):

```text
ai-service\venv\Scripts\pytest.exe -p no:cacheprovider -q \
  tests/test_signal_engine.py tests/test_signal_pipeline.py \
  tests/test_mt5_edge_cases.py tests/test_no_mt5_side_effects.py \
  tests/test_failure_scenarios.py
```

Result: **47 passed**.

## Signal baseline

The fixtures use deterministic M15 data, explicit indicator values, fake model
probabilities, and fake institutional analysis. The legacy live signal output
contains:

- pair, direction, confidence, strength
- entry, stop-loss, take-profit, ATR, risk/reward
- timestamp and fixed `regime: volatile`
- institutional bias, score, dealer pressure, liquidity state, and continuation probability

Observed deterministic examples:

| Case | Direction | Confidence | Entry | SL | TP | Result |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| aligned BUY | BUY | 0.800 | 1.10000 | 1.09750 | 1.10400 | accepted |
| aligned SELL | SELL | 0.800 | 1.10000 | 1.10250 | 1.09600 | accepted |

The separate `get_signal_from_row` backtest helper has different legacy
behavior: it returns only pair, signal, confidence, entry, SL, and TP, and uses
1.5 ATR SL / 2.5 ATR TP. This difference is recorded, not corrected.

Characterized no-signal behavior:

- ML and ICT disagreement returns `None`.
- Low confidence after H4/H1 penalties returns `None` below 0.50.
- ATR outside the helper's configured range returns `None`.
- Institutional score below 55 returns `None`.
- Missing market data returns `None`.
- Model prediction failure falls back to no ML signal and returns `None` when no valid signal remains.

The signal producer does not implement a standalone session, spread, or
expiry gate. Session and spread gates occur in `auto_trader_exness.py`. The
producer returns the literal `volatile` regime for accepted live signals; the
execution layer applies its own regime checks and defaults `UNKNOWN` to
`volatile`.

## Mock and cache baseline

`RealAITrader.use_mock_fallback` is false by default. When enabled, a failed
real signal invokes the existing mock generator. The mock behavior remains
non-deterministic across processes because it seeds from Python's hash and the
current minute; tests assert its existing shape and ranges without fixing it.

The cache representation is characterized from the existing
`ai-service/signals_cache.json` without writing to it:

```text
signals, version, last_update, saved_at
```

For a cached pair, `/signals/{pair}` returns `{signal: ..., cached: true}`.
For a missing pair, it invokes fresh analysis and returns
`{signal: ..., cached: false}`. There is no `expires_at` field and no automatic
stale-cache rejection in this boundary. The signal itself has a timestamp but
no expiry timestamp.

## Execution baseline

The fake execution path characterizes the following existing gates:

- session, confidence, regime/counter-trend, duplicate position, ATR, spread, and quality rejection
- position sizing and confidence-based sizing adjustment
- trade logging on accepted execution
- opposite-position and position lookup helpers
- trailing-stop and losing time-exit behavior

For an accepted deterministic `Live_Micro`-shaped account fixture, the
execution boundary passes the Exness-suffixed symbol `EURUSDm`, direction,
signal entry, derived SL/TP, confidence, and computed volume to the broker.
The confidence sizing adjustment raises the 0.01 base risk fraction by 20%
for confidence 0.80 before sizing; the captured volume is 0.80 lots with the
fixture's tick-value data.

`MT5Broker.place_market_order()` behavior is explicitly preserved in the
baseline:

- BUY uses `TRADE_ACTION_PENDING` and `ORDER_TYPE_BUY_LIMIT` at rounded ask.
- SELL uses `TRADE_ACTION_PENDING` and `ORDER_TYPE_SELL_LIMIT` at rounded bid.
- The initial request contains no `sl` or `tp` fields.
- Transient codes 10004, 10006, and 10013 retry.
- No-money and margin failures stop without an additional order.
- The returned ticket is the latest position ticket when available, otherwise `result.order`.

Trailing-stop characterization captures an `TRADE_ACTION_SLTP` request only
after profit exceeds one ATR and the proposed stop improves the current stop.
The time-exit path submits a pending close request for an old losing position
with comment `time_exit_loss`; profitable positions are left open.

The temporary in-memory TradeLogger characterization captures entry fields,
institutional fields, account, volume, ticket, exit fields, result, and reason
using the existing schema and update behavior.

## Characterization discrepancy — migration stopped

The expanded gate characterization found one behavior that differs from the
expected safety rule:

- A BUY signal for `EURUSD` with an existing opposite SELL position on
  `EURUSDm` reached the broker boundary instead of being rejected.
- The legacy `has_opposite()` implementation compares the position symbol
  directly with the unsuffixed signal pair. Therefore `EURUSDm` does not equal
  `EURUSD` and the opposite-position gate is bypassed for this suffix case.

The completed characterization suite now reports **29 passed**. The opposite
position behavior is asserted as the observed legacy acceptance and remains
listed above as a discrepancy rather than being corrected.

Potential production impact: opposite-position protection may not apply when
the broker position uses the Exness `m` suffix. This requires explicit review
and approval before any future migration or compatibility decision.

## Limitations and unresolved historical facts

- The complete historical configuration snapshot is unavailable. These tests
  do not claim historical configuration parity.
- Historical model binaries and exact historical MT5 bars were not available
  as deterministic fixtures; model behavior is represented by explicit fake
  probabilities.
- Signal timestamps are generated by the legacy clock and are validated for
  presence/format, not exact wall-clock equality.
- No live HTTP server was started. The endpoint function and serialized cache
  boundary were exercised directly.
- No real MT5 terminal, broker account, external network, or real order was
  used.

This report is a characterization record only. It is not authorization to
begin a canonical implementation or migration.
