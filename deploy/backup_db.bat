@echo off
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
mkdir deploy\backups 2>nul
copy ai-service\trades.db deploy\backups\trades_%TIMESTAMP%.db
echo Backup created: deploy\backups\trades_%TIMESTAMP%.db

