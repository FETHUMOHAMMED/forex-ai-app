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
