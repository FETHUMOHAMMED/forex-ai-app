# V4 CANONICAL EXPERIMENT - OFFICIAL STATUS

## PHASE: CONTROLLED EVIDENCE COLLECTION
## DAY: 29 of 90
## START DATE: 2026-08-23

## ⚠️ Evidence quality note (2026-09-20)

The runner experienced a hang bug from Sep 2 to Sep 20:
- MT5 calls could block indefinitely
- Heartbeats and signal logs stopped updating for up to 18 days
- Root cause: no timeout on mt5.initialize / copy_rates_from_pos, plus two runners competing for MT5

Fixed on 2026-09-20:
- Timeout wrappers added to all MT5 calls
- Heartbeat every 60s to prove liveness
- Error guards around signal evaluation and file writes
- Single runner enforced

**Evidence collected before 2026-09-20 should be considered suspect.**
Only evaluations from 2026-09-20 onward are trusted under the new runner.