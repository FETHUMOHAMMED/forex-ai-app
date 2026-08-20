
"""Health check endpoint for orchestration"""
from fastapi import APIRouter
from datetime import datetime, timezone
import sqlite3

router = APIRouter()

@router.get("/health")
def health_check():
    """Full system health check"""
    db_ok = False
    try:
        conn = sqlite3.connect("ai-service/trades.db")
        conn.execute("SELECT 1")
        conn.close()
        db_ok = True
    except:
        pass
    
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": db_ok,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
    }
