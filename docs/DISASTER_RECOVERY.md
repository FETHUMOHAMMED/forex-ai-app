# Disaster Recovery Plan

## Backup Strategy
- Location: deploy/backups/
- Frequency: Daily (manual or cron)
- Retention: 20 latest backups
- Verification: deploy/verify_backup.py

## Recovery Scenarios

### 1. Database Corruption
1. Stop all trading (kill switch)
2. Identify latest verified backup
3. Restore: copy backup to ai-service/trades.db
4. Verify with: python deploy/verify_backup.py
5. Resume trading only after verification

### 2. MT5 Terminal Crash
1. Kill switch: ENABLED
2. Check MT5 process
3. Restart MT5 terminal
4. Verify account connection
5. Check positions in MT5 vs DB
6. Reconcile orphans
7. Resume only if consistent

### 3. Process Crash
1. Watchdog auto-restarts
2. Check heartbeat
3. Verify no orphan positions
4. Check state consistency

### 4. Full System Restore
1. Clone repo (git clone)
2. Install dependencies (pip install -r requirements.txt)
3. Restore database from backup
4. Set environment variables (.env)
5. Start services (deploy/start_all.bat)
6. Verify: 103 tests pass, health checks pass
