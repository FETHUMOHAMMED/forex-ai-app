# Phase 17 — Identity Gate Reviewer Checklist

This checklist reviews a future sanitized evidence bundle. It does not assert that the bundle currently exists.

## Review rules

- Use exactly one source classification: BROKER FACT, APPLICATION FACT, RECORDED APPLICATION ARTIFACT, SYNTHETIC BEHAVIOR, INFERENCE, or UNKNOWN.
- Use confidence values PROVEN, STRONGLY INDICATED, INFERRED, or UNKNOWN.
- Use BLOCKED whenever required evidence is absent, incomplete, synthetic-only, or unproven.
- Never interpret legacy trades.ticket as a typed order, position, or deal identity.
- Never treat deal.position_id as deal.ticket.
- Never treat configuration flags or application hashes as broker evidence.

## Blocker checklist

| Phase 16 blocker | Evidence required | Current classification | Gate condition |
|---|---|---|---|
| Account/server scope | Trusted account snapshot with broker, login alias, server, environment, timestamp, provenance | UNKNOWN | PROVEN only with scoped source evidence |
| Account mode | Authoritative margin/account mode | UNKNOWN | PROVEN only from trusted account evidence |
| Order namespace | Authoritative semantics or explicitly scoped complete evidence | UNKNOWN | BLOCKED if based only on a finite sample |
| Position namespace | Same as order, with position lifecycle scope | UNKNOWN | BLOCKED until scope is established |
| Deal namespace | Deal records with source semantics and account scope | UNKNOWN | BLOCKED until scope is established |
| Order → deal → position lineage | Correlated request, result, snapshots, orders, and all deals | UNKNOWN | BLOCKED if any relationship is inferred |
| Multiple entry deals | Separate deal records for one order | UNKNOWN | CAPTURED or explicitly NOT_OBSERVED/UNAVAILABLE |
| Partial fill | Requested, filled, cumulative, and remaining quantities | UNKNOWN | BLOCKED without quantity-complete evidence |
| Partial close | Multiple exit deals and remaining position snapshots | UNKNOWN | BLOCKED without independent exit records |
| Full close | Complete close deal and position lifecycle | UNKNOWN | BLOCKED without broker-linked evidence |
| Close/reopen | Ordered old close and new order/position lineage | UNKNOWN | BLOCKED without both lifecycles |
| Same-symbol multiple positions | Before/after snapshots preserving all positions | UNKNOWN | BLOCKED if pre-existing positions are omitted |
| Multiple accounts | At least two account/server scopes with relation-preserving identifiers | UNKNOWN | BLOCKED with one account only |
| History ordering | Repeated retrieval batches preserving returned order | UNKNOWN | BLOCKED if chronology is assumed |
| Replay/duplicates | Repeated retrieval with source event IDs and digests | UNKNOWN | BLOCKED if application duplicates are mistaken for broker replay |
| Idempotency | Stable scoped source event identity | UNKNOWN | BLOCKED if based only on evidence hash or bare ticket |
| Maximum-ticket correlation | Request, result, before/after snapshots, selected ticket, and eventual lineage | UNKNOWN | BLOCKED if any component is missing |
| Newer module activation | Launcher/process/startup evidence | UNKNOWN | ACTIVE only with runtime/deployment proof |

## Required status interpretation

- PROVEN: directly supported by complete, trusted evidence.
- STRONGLY INDICATED: multiple repository-backed facts support it, but a broker guarantee is still absent.
- INFERRED: plausible interpretation; never sufficient for mapping.
- UNKNOWN: evidence insufficient.
- BLOCKED: the gate cannot progress for that item.

## Final reviewer decision

The overall identity gate may progress only when no critical item remains BLOCKED or UNKNOWN without an explicitly accepted conservative design rule. This checklist does not authorize production mapping or schema changes.

