# DAILY MONITORING ROUTINE

## EVERY MORNING (after 07:30 UTC):

### 1. Run Daily Report (new terminal, close after):
.\ai-service\venv\Scripts\python.exe tools/v4_daily_report.py

### 2. Check Heartbeat:
.\ai-service\venv\Scripts\python.exe tools/heartbeat_monitor.py

### 3. Record results in daily log
### 4. Close the terminal

## WHAT TO CHECK:
- Runner instances = 1 (not 0, not 2)
- Evaluations happening (not stuck)
- Safety violations = 0
- MT5 connected
- Qualified trades accumulating

## WHAT NOT TO DO:
- Don't restart the runner
- Don't check every hour
- Don't modify anything
- Don't panic if no trades

## DAILY LOG LOCATION:
research/paper/V4_CANONICAL_1.0/daily_log.md
