# AGENTS.md

This repository is a multi-service forex AI trading system with a Python AI service, a Node/Express backend, and a React frontend.

## Repository map
- [README.md](README.md) – top-level setup and launch overview.
- [docs/architecture.md](docs/architecture.md) – system modules and data flow.
- [docs/execution-flow.md](docs/execution-flow.md) – trading signal generation and execution path.
- [docs/database.md](docs/database.md) – schema and data conventions.
- [ai-service](ai-service) – Python daemon, trading logic, cache, and runtime helpers.
- [backend](backend) – Node.js API and websocket server.
- [frontend](frontend) – React dashboard.
- [scripts](scripts) – install/start helpers for local development.

## Working conventions
- Prefer small, localized changes that stay within one service boundary.
- Before changing signal generation, execution, risk logic, or database access, review the relevant docs first.
- Reuse the existing entry points in [scripts/install.sh](scripts/install.sh), [scripts/start.sh](scripts/start.sh), [docker-compose.yml](docker-compose.yml), and [start_forex_ai.bat](start_forex_ai.bat) rather than inventing new startup flows.
- Keep service ports and environment assumptions consistent with the repo defaults unless a change is explicitly required.

## Common commands
- Install dependencies: [scripts/install.sh](scripts/install.sh)
- Start local services: [scripts/start.sh](scripts/start.sh)
- Docker-based stack: [docker-compose.yml](docker-compose.yml)
- Windows launcher: [start_forex_ai.bat](start_forex_ai.bat)

## Safety and review guidance
- Do not change risk controls, execution gating, or data storage paths without checking the trading docs and related runtime modules.
- If an API or websocket contract changes, update the backend and frontend together.
- When modifying Python components, keep compatibility with the existing AI service runtime and cached signal format in mind.
- When modifying frontend or backend behavior, verify the relevant service still starts and responds before claiming success.
