# Phase 4 offline signal-serialization parity

Phase 4 validates the legacy V3 `GET /signals/{pair}` boundary without
starting FastAPI, opening a network socket, loading production cache state, or
connecting to MT5.

## Boundary

`ShadowSignalSerializationAdapter` delegates to a marked legacy endpoint and
wraps its returned payload in the same Starlette `JSONResponse` boundary used
by the offline comparison harness. It contains no signal-generation,
strategy, cache, risk, or execution logic.

The adapter is not imported by a production launcher and cannot be
constructed with an unmarked endpoint.

## Characterized behavior

- Cached BUY and SELL responses preserve the exact `signal`/`cached` shape,
  field names, omitted fields, numeric values, and JSON representation.
- Missing and invalid pairs are not validated by the legacy endpoint; they are
  passed to fresh analysis and can return HTTP 200 with `signal: null`.
- Endpoint-level signal-generation exceptions become HTTP 500 with the legacy
  `detail` payload.
- An uninitialized service becomes HTTP 503 with the legacy detail payload.
- Serialization exceptions propagate rather than being normalized.
- Existing stale cached signals return as cached without expiry rejection.
- Cached endpoint reads do not mutate the isolated service state.

## Timestamp comparison rule

The uncached signal producer creates `signal.timestamp` dynamically. The
parity test excludes only that exact nested field after proving the legacy and
shadow values differ. Every other field and response property is compared
exactly. No broad timestamp normalization is used.

## Verification

All tests use an in-memory service double, fake endpoint wrapper, and
Starlette response objects. No real HTTP, MT5, broker, database, cache,
configuration, or production runtime activity is used.
