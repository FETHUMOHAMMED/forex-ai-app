# FOREX-AI-APP Changelog

## v2.0.0 (2026-08-12) - Architecture Refactor
- Added domain model with invariants and error handling
- Implemented explicit position sizing with hard safety invariant
- Added MT5 ticket identity model (order/position/deal distinction)
- Created trade state machine with enforced transitions
- Added automated health monitoring (12 check types)
- Added order boundary risk gate (8 checks before MT5)
- Implemented isolated account workers (no shared MT5 state)
- Created canonical feature contract (H1 only)
- Added secrets manager (environment-based credentials)
- Moved 65+ ad-hoc scripts to archive/
- Added automated test suite (16/18 passing)
- Fixed "Invalid stops" error (exchange mode handling)
- Fixed heartbeat monitoring (standalone service)
- Fixed trade metadata (planned vs actual prices)
- Fixed account filtering (Live_Micro vs Demo2 separation)

## v1.0.0 - Initial Release
- Multi-account MT5 trading
- AI signal generation (ICT/SMC + XGBoost)
- Risk management filters
- Telegram/Slack notifications
- React dashboard
- FastAPI backend
