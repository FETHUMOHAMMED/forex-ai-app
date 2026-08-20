# Execution Flow

## Signal Generation (Daemon)
1. Fetch 500 M15 bars from MT5
2. ML model prediction (BUY/SELL + confidence)
3. ICT pattern detection (MSS, OB, FVG, BB, LV)
4. Institutional analysis (Microstructure + Liquidity + Structure)
5. Counter-trend penalty (H1 bias check)
6. Institutional score filter (>=55)
7. Signal cached to HTTP endpoint (port 8001)

## Trade Execution (Watchdog)
1. Config reload (every cycle)
2. Session filter (London/Asian/NY)
3. Tick freshness check (<300s)
4. Signal fetch from daemon cache
5. Confidence gate (>=0.53)
6. Quality scoring (Grade A/B/C/D)
7. Position duplicate check
8. Exposure limit check
9. Position sizing (0.05% risk)
10. Order execution via MT5
11. Position management (trailing stop, breakeven, timeout)

## Position Management
- Timeout: Close if open >24h
- Breakeven: Move SL to entry at 0.5R
- Trailing stop: Activate at 1R, trail 30%
