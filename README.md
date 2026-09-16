# FOREX-AI-APP

**Automated trading research platform with verified execution safety.**

> Status: Research / Validation mode. Feature freeze in effect as of 2026-09-14.

---

## What This Is

A production-grade Python system for developing, testing, and — in controlled mode — executing automated forex strategies.

**This is not a "get rich" trading bot.** It is a research platform that enforces reproducibility, safety, and auditability before any strategy is allowed near real capital.

## Core Engineering Properties

- **Single execution path.** Only one file in the entire codebase is allowed to submit orders to MetaTrader 5. Verified by AST analysis, not convention.
- **Hard safety boundary.** Every order passes 14+ validation checks before reaching the broker. Fails closed, not open.
- **Signal-level parity.** 40,000 / 40,000 historical vs live signal comparisons matched exactly.
- **Kill switch.** Halts trading immediately.
- **Full audit trail.** Every decision, order, and outcome is logged with evidence.
- **138 automated tests** covering safety, parity, failure injection, and reconciliation.

## Architecture
Strategy (frozen, versioned)
↓
Orchestrator (live_micro_runner)
↓
Hard Safety Boundary (14+ checks, immutable limits)
↓
Single Execution Path (only file allowed to call MT5)
↓
MetaTrader 5 / Broker

text

## Stack

- Python
- MetaTrader 5 Python API
- FastAPI (backend)
- React (frontend)
- SQLite / PostgreSQL
- pytest
- Docker

## Project Structure
packages/
strategy/ Frozen strategy definitions
execution/ Safety boundary, single path, orchestrator
research/ Backtesting, replay, parity tests
integrity/ Failure injection, runtime gates
risk/ Risk management
persistence/ Schema + evidence storage

tools/ 60+ validation and research scripts
tests/ 138 tests (safety, parity, integration)
research/ Experiment evidence and reports

text

## Current Focus

Forward-testing the V4 strategy. Question under investigation: does V4 survive paper trading well enough to justify controlled real-money testing?

## Contact

**Fethu Mohammed** — Python / FastAPI / React Developer
GitHub: [@FETHUMOHAMMED](https://github.com/FETHUMOHAMMED)